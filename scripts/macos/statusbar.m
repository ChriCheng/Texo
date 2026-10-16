#import <AppKit/AppKit.h>
#include <math.h>
#include <stdbool.h>

typedef void (*TexoStatusCallback)(int);
extern unsigned int TexoGetShortcutModifiers(int action);
extern const char *TexoGetShortcutLabel(int action);
extern NSString *TexoShortcutCharacter(int action);

@interface TexoStatusController : NSObject
@property(nonatomic, strong) NSStatusItem *item;
@property(nonatomic, strong) NSMenu *menu;
@property(nonatomic, strong) NSMenuItem *loginItem;
@property(nonatomic, strong) NSArray<NSMenuItem *> *formatItems;
@property(nonatomic, strong) NSArray<NSMenuItem *> *modeItems;
@property(nonatomic, strong) NSImage *normalImage;
@property(nonatomic, strong) NSTimer *progressTimer;
@property(nonatomic, assign) double progress;
@property(nonatomic, assign) double targetProgress;
@property(nonatomic, assign) TexoStatusCallback callback;
- (NSMenuItem *)addItem:(NSString *)title tag:(NSInteger)tag to:(NSMenu *)menu key:(NSString *)key modifiers:(NSEventModifierFlags)modifiers;
- (void)drawProgress;
@end

@implementation TexoStatusController
- (NSMenuItem *)addItem:(NSString *)title tag:(NSInteger)tag to:(NSMenu *)menu key:(NSString *)key modifiers:(NSEventModifierFlags)modifiers {
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:@selector(selected:) keyEquivalent:key];
    item.tag = tag;
    item.target = self;
    item.keyEquivalentModifierMask = modifiers;
    [menu addItem:item];
    return item;
}

- (void)selected:(NSMenuItem *)sender {
    if (self.callback) {
        self.callback((int)sender.tag);
    }
}
- (void)drawProgress {
    double progress = self.progress;
    NSImage *image = [NSImage imageWithSize:NSMakeSize(18, 18) flipped:NO drawingHandler:^BOOL(NSRect __unused rect) {
        [NSColor.blackColor set];
        NSBezierPath *circle = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(2, 2, 14, 14)];
        circle.lineWidth = 1.2;
        [circle stroke];
        if (progress >= 1) {
            [circle fill];
        } else if (progress > 0) {
            NSBezierPath *sector = [NSBezierPath bezierPath];
            [sector moveToPoint:NSMakePoint(9, 9)];
            [sector appendBezierPathWithArcWithCenter:NSMakePoint(9, 9) radius:7 startAngle:90 endAngle:90 - 360 * progress clockwise:YES];
            [sector closePath];
            [sector fill];
        }
        return YES;
    }];
    image.template = YES;
    self.item.button.image = image;
}
- (void)animateProgress:(NSTimer *)timer {
    // Smooth only work already confirmed by the OCR worker.
    double remaining = self.targetProgress - self.progress;
    self.progress = remaining <= 0.002 ? self.targetProgress : self.progress + remaining * 0.35;
    [self drawProgress];
    if (self.progress >= self.targetProgress) {
        [timer invalidate];
        self.progressTimer = nil;
    }
}
@end

static TexoStatusController *controller;
static NSString *shortcutTooltip(void) {
    return [NSString stringWithFormat:@"Texo · 点击显示菜单；%@ 截图；%@ 显示／收起结果",
        [NSString stringWithUTF8String:TexoGetShortcutLabel(0)], [NSString stringWithUTF8String:TexoGetShortcutLabel(1)]];
}

void TexoRefreshShortcutPresentation(void) {
    if (!NSThread.isMainThread || !controller) {
        return;
    }
    for (int action = 0; action < 2; action++) {
        NSMenuItem *item = [controller.menu itemWithTag:action == 0 ? 2 : 1];
        unsigned int modifiers = TexoGetShortcutModifiers(action);
        item.keyEquivalent = TexoShortcutCharacter(action);
        item.keyEquivalentModifierMask = ((modifiers & 256) ? NSEventModifierFlagCommand : 0)
            | ((modifiers & 512) ? NSEventModifierFlagShift : 0)
            | ((modifiers & 2048) ? NSEventModifierFlagOption : 0)
            | ((modifiers & 4096) ? NSEventModifierFlagControl : 0);
    }
    if (controller.progress < 0) {
        controller.item.button.toolTip = shortcutTooltip();
    }
}

__attribute__((visibility("default")))
void *TexoStatusItemButton(void) {
    return NSThread.isMainThread ? (__bridge void *)controller.item.button : NULL;
}

__attribute__((visibility("default")))
int TexoGetCopyFormat(void) {
    if (!NSThread.isMainThread) {
        return 2;
    }
    NSNumber *saved = [NSUserDefaults.standardUserDefaults objectForKey:@"TexoCopyFormat"];
    NSInteger value = saved ? saved.integerValue : 2;
    return value >= 0 && value <= 2 ? (int)value : 2;
}

__attribute__((visibility("default")))
void TexoSetCopyFormat(int format) {
    if (!NSThread.isMainThread || format < 0 || format > 2) {
        return;
    }
    [NSUserDefaults.standardUserDefaults setInteger:format forKey:@"TexoCopyFormat"];
    for (NSUInteger index = 0; index < controller.formatItems.count; index++) {
        controller.formatItems[index].state = (int)index == format ? NSControlStateValueOn : NSControlStateValueOff;
    }
}

__attribute__((visibility("default")))
int TexoGetRecognitionMode(void) {
    if (!NSThread.isMainThread) {
        return 0;
    }
    NSInteger value = [NSUserDefaults.standardUserDefaults integerForKey:@"TexoRecognitionMode"];
    return value == 1 ? 1 : 0;
}

__attribute__((visibility("default")))
void TexoSetRecognitionMode(int mode) {
    if (!NSThread.isMainThread || (mode != 0 && mode != 1)) {
        return;
    }
    [NSUserDefaults.standardUserDefaults setInteger:mode forKey:@"TexoRecognitionMode"];
    for (NSUInteger index = 0; index < controller.modeItems.count; index++) {
        controller.modeItems[index].state = (int)index == mode ? NSControlStateValueOn : NSControlStateValueOff;
    }
}

__attribute__((visibility("default")))
bool TexoInstallStatusItem(TexoStatusCallback callback) {
    if (!NSThread.isMainThread || !callback || controller) {
        return false;
    }
    [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    controller = [[TexoStatusController alloc] init];
    controller.callback = callback;
    controller.progress = -1;
    controller.targetProgress = -1;
    controller.item = [NSStatusBar.systemStatusBar statusItemWithLength:NSSquareStatusItemLength];
    NSString *project = [NSBundle.mainBundle objectForInfoDictionaryKey:@"TexoProjectRoot"];
    NSImage *image = project ? [[NSImage alloc] initWithContentsOfFile:[project stringByAppendingPathComponent:@"assets/svg/status-icon.svg"]] : nil;
    if (!image) {
        image = [NSImage imageWithSystemSymbolName:@"doc.text.viewfinder" accessibilityDescription:@"Texo"];
    }
    image.template = YES;
    image.size = NSMakeSize(18, 18);
    controller.normalImage = image;
    controller.item.button.image = image;
    controller.item.button.toolTip = shortcutTooltip();
    controller.item.button.accessibilityLabel = @"Texo";

    controller.menu = [[NSMenu alloc] initWithTitle:@"Texo"];
    [controller addItem:@"截图识别" tag:2 to:controller.menu key:@"l" modifiers:NSEventModifierFlagCommand];
    [controller addItem:@"选择图片" tag:6 to:controller.menu key:@"" modifiers:0];
    [controller addItem:@"识别剪贴板" tag:3 to:controller.menu key:@"" modifiers:0];
    [controller.menu addItem:NSMenuItem.separatorItem];
    [controller addItem:@"显示／收起结果" tag:1 to:controller.menu key:@";" modifiers:NSEventModifierFlagCommand | NSEventModifierFlagShift];
    [controller addItem:@"复制结果" tag:7 to:controller.menu key:@"" modifiers:0];
    [controller addItem:@"PPT 专用复制" tag:9 to:controller.menu key:@"" modifiers:0];
    [controller.menu addItem:NSMenuItem.separatorItem];
    NSMenu *settings = [[NSMenu alloc] initWithTitle:@"设定"];
    NSMenuItem *settingsItem = [[NSMenuItem alloc] initWithTitle:@"设定" action:nil keyEquivalent:@""];
    settingsItem.submenu = settings;
    [controller.menu addItem:settingsItem];
    NSMenu *modes = [[NSMenu alloc] initWithTitle:@"识别模式"];
    NSMenuItem *modeItem = [[NSMenuItem alloc] initWithTitle:@"识别模式" action:nil keyEquivalent:@""];
    modeItem.submenu = modes;
    [settings addItem:modeItem];
    controller.modeItems = @[
        [controller addItem:@"中文与公式" tag:20 to:modes key:@"" modifiers:0],
        [controller addItem:@"公式" tag:21 to:modes key:@"" modifiers:0]
    ];
    NSMenu *formats = [[NSMenu alloc] initWithTitle:@"公式复制格式"];
    NSMenuItem *formatItem = [[NSMenuItem alloc] initWithTitle:@"公式复制格式" action:nil keyEquivalent:@""];
    formatItem.submenu = formats;
    [settings addItem:formatItem];
    controller.formatItems = @[
        [controller addItem:@"公式" tag:10 to:formats key:@"" modifiers:0],
        [controller addItem:@"$公式$" tag:11 to:formats key:@"" modifiers:0],
        [controller addItem:@"$$公式$$" tag:12 to:formats key:@"" modifiers:0]
    ];
    [settings addItem:NSMenuItem.separatorItem];
    [controller addItem:@"快捷键设置…" tag:30 to:settings key:@"" modifiers:0];
    controller.loginItem = [controller addItem:@"登录时自动启动" tag:4 to:settings key:@"" modifiers:0];
    [controller.menu addItem:NSMenuItem.separatorItem];
    [controller addItem:@"退出 Texo" tag:5 to:controller.menu key:@"q" modifiers:NSEventModifierFlagCommand];
    TexoSetCopyFormat(TexoGetCopyFormat());
    TexoSetRecognitionMode(TexoGetRecognitionMode());
    TexoRefreshShortcutPresentation();
    controller.item.menu = controller.menu;
    return true;
}

__attribute__((visibility("default")))
void TexoSetLoginEnabled(bool enabled) {
    if (NSThread.isMainThread) {
        controller.loginItem.state = enabled ? NSControlStateValueOn : NSControlStateValueOff;
    }
}

__attribute__((visibility("default")))
void TexoSetRecognitionProgress(double value, const char *label) {
    if (!NSThread.isMainThread || !controller) {
        return;
    }
    if (value == -2) {
        [controller.progressTimer invalidate];
        controller.progressTimer = nil;
        return;
    }
    if (value < 0 || !isfinite(value)) {
        [controller.progressTimer invalidate];
        controller.progressTimer = nil;
        controller.progress = -1;
        controller.targetProgress = -1;
        controller.item.button.image = controller.normalImage;
        controller.item.button.toolTip = shortcutTooltip();
        return;
    }
    if (value == 0 || controller.progress < 0) {
        [controller.progressTimer invalidate];
        controller.progressTimer = nil;
        controller.progress = 0;
        controller.targetProgress = 0;
        [controller drawProgress];
    }
    controller.targetProgress = fmax(controller.targetProgress, fmin(1, value));
    NSString *text = label ? [NSString stringWithUTF8String:label] : nil;
    controller.item.button.toolTip = text.length ? [@"Texo · " stringByAppendingString:text] : @"Texo · 正在识别";
    if (controller.progress < controller.targetProgress && !controller.progressTimer) {
        controller.progressTimer = [NSTimer timerWithTimeInterval:1.0 / 30 target:controller selector:@selector(animateProgress:) userInfo:nil repeats:YES];
        [NSRunLoop.mainRunLoop addTimer:controller.progressTimer forMode:NSRunLoopCommonModes];
    }
}

__attribute__((visibility("default")))
void TexoRemoveStatusItem(void) {
    if (!NSThread.isMainThread || !controller) {
        return;
    }
    controller.callback = NULL;
    [controller.progressTimer invalidate];
    controller.progressTimer = nil;
    controller.item.menu = nil;
    [NSStatusBar.systemStatusBar removeStatusItem:controller.item];
    controller = nil;
}
