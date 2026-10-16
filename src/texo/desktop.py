from io import BytesIO
from queue import Empty, Queue
import re
from threading import Thread
import time

from texo.latex import normalize_latex
from texo.login import login_enabled, set_login_enabled
from texo.macos import GlobalHotkey, capture_image, read_clipboard_image
from texo.popover import NativePopover
from texo.statusbar import StatusBar


def _single_formula(text):
    for delimiter in ("$$", "$"):
        if len(text) >= 2 * len(delimiter) and text.startswith(delimiter) and text.endswith(delimiter):
            latex = text[len(delimiter):-len(delimiter)].strip()
            # Escaped dollars are formula text; unescaped dollars delimit other content.
            if not re.search(r"(?<!\\)(?:\\\\)*\$", latex):
                return latex
    return None


class NativeOCRWindow:
    """Drive native UI on the main thread; acquisition and OCR stay in workers."""

    def __init__(self, root, model_dir, recognize, open_image, mode=None):
        self.root, self.model_dir = root, model_dir
        self.recognize, self.open_image = recognize, open_image
        self.events = Queue()
        self.busy = self.interaction_active = self.login_busy = False
        self.shortcuts_active = False
        self.hotkeys = []
        self.statusbar = StatusBar(self.events.put)
        try:
            self.panel = NativePopover(self.events.put)
        except Exception:
            self.statusbar.close()
            raise
        if mode is not None:
            self.panel.set_mode(0 if mode == "mixed" else 1)
        self.result_mode = self.panel.get_mode()
        self.panel.set_result_mode(self.result_mode)
        root.bind("<Destroy>", self.close, add="+")
        root.createcommand("::tk::mac::ReopenApplication", self.show)
        root.createcommand("::tk::mac::Quit", root.destroy)
        try:
            self.statusbar.set_login_enabled(login_enabled())
        except RuntimeError as error:
            self.panel.set_status(str(error))
        shortcuts = self.statusbar.get_shortcuts()
        self.panel.set_capture_shortcut(shortcuts[0]["label"])
        try:
            self.register_hotkeys(shortcuts)
        except RuntimeError as error:
            self.panel.set_status(str(error))
        root.after(30, self.poll)

    def show(self):
        if self.shortcuts_active:
            self.statusbar.show_shortcut_settings()
        elif not self.interaction_active:
            self.panel.show()

    def toggle(self):
        if self.panel.is_shown():
            self.panel.hide()
        else:
            self.show()

    def close(self, event):
        if event.widget is self.root:
            self.panel.close()
            self.statusbar.close()
            self.release_hotkeys()

    def release_hotkeys(self):
        for hotkey in self.hotkeys:
            hotkey.close()
        self.hotkeys.clear()

    def register_hotkeys(self, shortcuts):
        registered = []
        try:
            for identifier, (shortcut, action) in enumerate(zip(shortcuts, (2, 1)), 1):
                registered.append(GlobalHotkey(lambda action=action: self.events.put(action), identifier=identifier, **shortcut))
        except RuntimeError:
            for hotkey in registered:
                hotkey.close()
            raise
        self.hotkeys = registered

    def open_shortcut_settings(self):
        if self.shortcuts_active:
            self.statusbar.show_shortcut_settings()
            return
        if self.busy:
            return
        self.panel.hide(immediately=True)
        self.release_hotkeys()
        self.shortcuts_active = True
        if not self.statusbar.show_shortcut_settings():
            self.cancel_shortcut_settings()
            self.panel.set_status("无法打开快捷键设置。")
            self.show()

    def cancel_shortcut_settings(self):
        if not self.shortcuts_active:
            return
        self.shortcuts_active = False
        self.statusbar.close_shortcut_settings()
        try:
            self.register_hotkeys(self.statusbar.get_shortcuts())
        except RuntimeError as error:
            self.panel.set_status(str(error))
            self.show()

    def save_shortcut_settings(self):
        if not self.shortcuts_active:
            return
        shortcuts = self.statusbar.get_shortcuts(draft=True)
        try:
            self.register_hotkeys(shortcuts)
            if not self.statusbar.commit_shortcuts():
                raise RuntimeError("快捷键无效，请重新设置。")
        except RuntimeError as error:
            self.release_hotkeys()
            self.statusbar.set_shortcut_error(str(error))
            return
        self.shortcuts_active = False
        self.statusbar.close_shortcut_settings()
        self.panel.set_capture_shortcut(shortcuts[0]["label"])
        self.panel.set_status("快捷键已保存并立即生效。")

    def set_busy(self, busy):
        self.busy = busy
        self.panel.set_busy(busy)
        if not busy:
            self.statusbar.set_progress(-1)

    def poll(self):
        actions = {1: self.toggle, 2: self.screenshot, 3: self.clipboard, 4: self.toggle_login, 5: self.root.destroy, 6: self.choose, 7: self.copy, 9: self.copy_ppt, 30: self.open_shortcut_settings, 31: self.save_shortcut_settings, 32: self.cancel_shortcut_settings}
        while True:
            try:
                event = self.events.get_nowait()
            except Empty:
                break
            if isinstance(event, int):
                if 10 <= event <= 12:
                    self.panel.set_format(event - 10)
                    self.format_result()
                    continue
                if event in (20, 21):
                    self.panel.set_mode(event - 20)
                    continue
                if event in actions:
                    actions[event]()
                    if event == 5:
                        return
                continue
            kind, value, detail, error = event
            if kind == "image":
                was_shown, label = detail
                self.interaction_active = False
                self.set_busy(False)
                if error:
                    self.panel.set_status(error)
                    self.show()
                elif value is None:
                    self.panel.set_status("已取消截图，保留上次结果。")
                    if was_shown:
                        self.show()
                else:
                    self.start(value, label)
            elif kind == "result":
                if not error and self.result_mode == 0 and value:
                    formula = _single_formula(value.strip())
                    if formula is not None:
                        value, self.result_mode = formula, 1
                self.panel.set_result_mode(self.result_mode)
                self.panel.set_result(value or "", reset_undo=True)
                self.panel.set_status(f"识别失败：{error}" if error else f"识别完成 · {detail:.2f} 秒，请核对后使用。")
                self.set_busy(False)
                if not error and self.copy(automatic=True):
                    self.panel.set_status(f"识别完成 · {detail:.2f} 秒 · 已自动复制。")
                self.show()
            elif kind == "progress":
                if value is not None:
                    self.statusbar.set_progress(value, detail)
                self.panel.set_status(detail)
            elif kind == "office":
                self.set_busy(False)
                if not error:
                    try:
                        if not self.panel.copy_office(value):
                            raise RuntimeError("无法写入剪贴板，请重试。")
                    except Exception as failure:
                        error = str(failure)
                self.panel.set_status(f"PPT 复制失败：{error}" if error else "PPT 内容已复制，可直接粘贴到 PowerPoint。")
            elif kind == "login":
                self.login_busy = False
                if error:
                    self.panel.set_status(f"无法更新自动启动：{error}")
                    self.show()
                else:
                    self.statusbar.set_login_enabled(value)
                    self.panel.set_status("已开启登录时自动启动。" if value else "已关闭登录时自动启动。")
        self.root.after(30, self.poll)

    def screenshot(self):
        self.acquire(capture_image, "截图", capture=True)

    def clipboard(self):
        self.acquire(read_clipboard_image, "剪贴板图片")

    def acquire(self, get_image, label, capture=False):
        if self.busy or self.shortcuts_active:
            return
        was_shown = self.panel.is_shown()
        self.panel.hide(immediately=True)
        self.interaction_active = capture
        self.set_busy(True)
        self.panel.set_status("请框选文字或公式，Esc 取消。" if capture else "正在读取剪贴板…")
        events = self.events

        def worker():
            try:
                events.put(("image", get_image(), (was_shown, label), None))
            except Exception as error:
                events.put(("image", None, (was_shown, label), str(error)))

        self.root.after(200 if capture else 0, lambda: Thread(target=worker, daemon=True).start())

    def choose(self):
        if self.busy or self.shortcuts_active:
            return
        from tkinter import filedialog

        was_shown = self.panel.is_shown()
        self.panel.hide()
        self.interaction_active = True
        self.set_busy(True)
        path = ""
        failed = False
        try:
            # A sheet attached to the hidden Tk root can reveal it and stall its timers.
            path = filedialog.askopenfilename(title="选择文字或公式图片", filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("所有文件", "*")])
        except Exception as error:
            failed = True
            self.panel.set_status(f"无法选择图片：{error}")
        finally:
            self.interaction_active = False
            self.set_busy(False)
        if path:
            self.start(path, "图片")
        elif was_shown or failed:
            self.show()

    def start(self, source, label):
        if self.busy:
            return
        try:
            image = self.open_image(source)
            png = BytesIO()
            image.save(png, "PNG")
        except Exception as error:
            self.panel.set_status(f"无法打开图片：{error}")
            self.show()
            return
        self.result_mode = self.panel.get_mode()
        self.panel.set_result_mode(self.result_mode)
        self.panel.set_image(png.getvalue())
        self.panel.set_result("", reset_undo=True)
        self.panel.set_status(f"正在识别 {label}…")
        self.set_busy(True)
        self.statusbar.set_progress(0, f"正在识别 {label}…")
        events, recognize, model_dir = self.events, self.recognize, self.model_dir
        mode = "mixed" if self.result_mode == 0 else "formula"

        def worker():
            started = time.monotonic()
            try:
                progress = lambda value, message: events.put(("progress", value, message, None))
                events.put(("result", recognize(image, model_dir, mode, progress=progress), time.monotonic() - started, None))
            except Exception as error:
                events.put(("result", None, 0, str(error)))

        Thread(target=worker, daemon=True).start()

    def format_result(self):
        current = self.panel.get_result()
        text = current.strip()
        if self.result_mode == 1:
            formula = _single_formula(text)
            text = normalize_latex(text if formula is None else formula)
            delimiter = ("", "$", "$$")[self.panel.get_format()]
            text = f"{delimiter}{text}{delimiter}" if text else ""
        if text != current:
            self.panel.set_result(text)
        return text

    def copy(self, automatic=False):
        text = self.format_result()
        if automatic:
            self.panel.reset_undo()
        if text:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
            except Exception as error:
                self.panel.set_status(f"复制失败：{error}")
                return False
            if not automatic:
                self.panel.set_status("结果已复制。")
            return True
        return False

    def copy_ppt(self):
        if self.busy or self.shortcuts_active:
            return
        text = self.format_result()
        if not text:
            return
        pure_latex = self.result_mode == 1
        self.set_busy(True)
        self.panel.set_status("正在准备 PPT 复制…")

        def worker():
            try:
                from texo.office import make_office_payload

                self.events.put(("office", make_office_payload(text, pure_latex=pure_latex), None, None))
            except Exception as error:
                self.events.put(("office", None, None, str(error)))

        Thread(target=worker, daemon=True).start()

    def toggle_login(self):
        if self.login_busy:
            return
        try:
            enabled = not login_enabled()
        except RuntimeError as error:
            self.panel.set_status(str(error))
            self.show()
            return
        self.login_busy = True
        events = self.events

        def worker():
            try:
                set_login_enabled(enabled)
                events.put(("login", enabled, None, None))
            except Exception as error:
                events.put(("login", False, None, str(error)))

        Thread(target=worker, daemon=True).start()
