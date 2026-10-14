# Texo OCR

Texo converts formula images into editable LaTeX, or single-column Chinese text
and formula screenshots into Markdown on macOS.

## Language

**Recognition result**: The formula source decoded from an image, with equivalent command aliases made compatible with the user's math renderer. It does not reconstruct content outside the image.

**Copy format**: The recognition result copied as plain LaTeX, inline math enclosed in single dollar signs, or display math enclosed in double dollar signs. No format includes a trailing newline.

**Mixed result**: Chinese/English prose in reading order, with detected inline
formulas enclosed in single dollar signs and display formulas in double dollar
signs. Copy preserves the complete Markdown without wrapping the prose in math.

**Recognition mode**: Formula mode sends one formula to Texo. Mixed mode detects
formula regions with Pix2Text MFD, recognizes those crops with Texo, and reads
the remaining text with macOS Vision. Images remain local.

**Clipboard image**: Image data currently on the macOS clipboard, rather than a path copied as text.

**Temporary capture**: A user-selected screen region used for recognition without leaving a screenshot on the desktop.

**Global shortcut**: A key combination that triggers Texo while another application is in front, for as long as Texo is running.

**Resident popover**: The native white menu-bar interface with image preview on
the left and editable result on the right. Clicking the menu-bar icon or global
Command-Shift-semicolon toggles it; Escape or an outside click hides it without
quitting. Global Command-L first starts region selection, then displays the
captured image and recognition progress. Shortcut rebinding is not yet available.

**Login startup**: Opens Texo.app in the background after login, with the popover
hidden. Quitting does not restart the app immediately and leaves the next-login
setting enabled; disabling startup does not quit the current app. The menu-bar
icon's right-click menu controls startup and quitting.

**Local application**: A native Texo.app that runs the existing Python environment
in the same process. LaunchServices opens one instance and macOS attributes its
window and screenshot permissions to Texo. It requires the current checkout,
virtual environment, models and base Python paths to stay available.
The native app stays in the menu bar without a Dock icon; quitting
releases its shortcuts. The terminal-launched Tk window remains a fallback.

**Maintenance branch**: Local macOS changes are published only to
`origin/codex/macos-local-ocr` in `ChriCheng/Texo`; neither `main` nor the upstream
repository is a push or merge target.
