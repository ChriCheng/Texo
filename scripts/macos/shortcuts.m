#import <AppKit/AppKit.h>
#include <stdbool.h>

extern void TexoRefreshShortcutPresentation(void);
typedef void (*TexoShortcutCallback)(int);

static NSArray<NSDictionary *> *defaultShortcuts(void) {
    return @[
        @{@"key": @37, @"modifiers": @256, @"character": @"l"},
        @{@"key": @41, @"modifiers": @768, @"character": @";"}
    ];
}

static NSString *shortcutError(NSDictionary *shortcut) {
    if (![shortcut isKindOfClass:NSDictionary.class]
        || ![shortcut[@"key"] isKindOfClass:NSNumber.class]
        || ![shortcut[@"modifiers"] isKindOfClass:NSNumber.class]
        || ![shortcut[@"character"] isKindOfClass:NSString.class]) {
        return @"快捷键数据无效，请重新录制。";
    }
    NSInteger key = [shortcut[@"key"] integerValue];
    NSUInteger modifiers = [shortcut[@"modifiers"] unsignedIntegerValue];
    NSString *character = shortcut[@"character"];
    if (key < 0 || key > 126 || (key >= 54 && key <= 63) || key == 53 || !character.length) {
        return @"请选择字母、数字、符号或功能键。Esc 用于取消录制。";
    }
    if ((modifiers & ~(256 | 512 | 2048 | 4096)) || !(modifiers & (256 | 2048 | 4096))) {
        return @"快捷键必须包含 ⌘、⌃ 或 ⌥，不能只用普通按键或 ⇧。";
    }
    NSSet *editingKeys = [NSSet setWithArray:@[@"a", @"c", @"x", @"v", @"z", @"q", @"w", @"h", @"m", @"s", @"f", @"p", @"n", @"o"]];
    if ((modifiers & 256) && !(modifiers & (2048 | 4096)) && [editingKeys containsObject:character.lowercaseString]) {
        return @"此组合用于常见编辑或窗口操作；请增加 ⌃／⌥，或选择其他按键。";
    }
    return nil;
}

static NSString *shortcutsError(NSArray *shortcuts) {
    if (![shortcuts isKindOfClass:NSArray.class] || shortcuts.count != 2) {
        return @"需要分别设置截图和显示／收起快捷键。";
    }
    for (NSDictionary *shortcut in shortcuts) {
        NSString *error = shortcutError(shortcut);
        if (error) {
            return error;
        }
    }
    if ([shortcuts[0][@"key"] isEqual:shortcuts[1][@"key"]]
        && [shortcuts[0][@"modifiers"] isEqual:shortcuts[1][@"modifiers"]]) {
        return @"两个功能不能使用相同的快捷键。";
    }
    return nil;
}

static NSArray<NSDictionary *> *savedShortcuts(void) {
    NSArray *saved = [NSUserDefaults.standardUserDefaults objectForKey:@"TexoShortcuts"];
    return shortcutsError(saved) ? defaultShortcuts() : saved;
}

static NSString *shortcutLabel(NSDictionary *shortcut) {
    NSUInteger modifiers = [shortcut[@"modifiers"] unsignedIntegerValue];
    NSMutableString *label = [NSMutableString string];
    if (modifiers & 4096) [label appendString:@"⌃"];
    if (modifiers & 2048) [label appendString:@"⌥"];
    if (modifiers & 256) [label appendString:@"⌘"];
    if (modifiers & 512) [label appendString:@"⇧"];
    NSString *character = shortcut[@"character"];
    NSDictionary *special = @{@49: @"空格", @36: @"↩", @48: @"⇥", @51: @"⌫", @76: @"⌅", @117: @"⌦", @123: @"←", @124: @"→", @125: @"↓", @126: @"↑"};
    NSString *keyLabel = special[shortcut[@"key"]];
    if (!keyLabel && character.length == 1) {
        unichar value = [character characterAtIndex:0];
        if (value >= NSF1FunctionKey && value <= NSF35FunctionKey) {
            keyLabel = [NSString stringWithFormat:@"F%d", value - NSF1FunctionKey + 1];
        }
    }
    [label appendString:keyLabel ?: character.uppercaseString];
    return label;
}

__attribute__((visibility("default")))
int TexoGetShortcutKey(int action) {
    return NSThread.isMainThread && action >= 0 && action <= 1 ? [savedShortcuts()[action][@"key"] intValue] : -1;
}

__attribute__((visibility("default")))
unsigned int TexoGetShortcutModifiers(int action) {
    return NSThread.isMainThread && action >= 0 && action <= 1 ? [savedShortcuts()[action][@"modifiers"] unsignedIntValue] : 0;
}

NSString *TexoShortcutCharacter(int action) {
    return NSThread.isMainThread && action >= 0 && action <= 1 ? savedShortcuts()[action][@"character"] : @"";
}

static NSString *labelSnapshot;
__attribute__((visibility("default")))
const char *TexoGetShortcutLabel(int action) {
    if (!NSThread.isMainThread || action < 0 || action > 1) {
        return "";
    }
    labelSnapshot = shortcutLabel(savedShortcuts()[action]);
    return labelSnapshot.UTF8String;
}

@interface TexoShortcutController : NSObject <NSWindowDelegate>
@property(nonatomic, strong) NSPanel *panel;
@property(nonatomic, strong) NSArray<NSButton *> *recordButtons;
@property(nonatomic, strong) NSTextField *errorLabel;
@property(nonatomic, strong) NSMutableArray<NSDictionary *> *draft;
@property(nonatomic, strong) id eventMonitor;
@property(nonatomic, assign) NSInteger recordingAction;
@property(nonatomic, assign) TexoShortcutCallback callback;
- (void)refreshButtons;
- (void)recordEvent:(NSEvent *)event;
@end

static TexoShortcutController *shortcutController;

@implementation TexoShortcutController
- (void)refreshButtons {
    for (NSUInteger action = 0; action < self.recordButtons.count; action++) {
        self.recordButtons[action].title = self.recordingAction == (NSInteger)action
            ? @"请按组合键…" : [shortcutLabel(self.draft[action]) stringByAppendingString:@"　点击录制"];
    }
}
- (void)beginRecording:(NSButton *)sender {
    self.recordingAction = sender.tag;
    self.errorLabel.textColor = NSColor.secondaryLabelColor;
    self.errorLabel.stringValue = @"按下新的组合键；按 Esc 取消本次录制。";
    [self refreshButtons];
}
- (void)recordEvent:(NSEvent *)event {
    if (event.keyCode == 53) {
        self.recordingAction = -1;
        self.errorLabel.textColor = NSColor.secondaryLabelColor;
        self.errorLabel.stringValue = @"录制已取消，设置尚未改变。";
        [self refreshButtons];
        return;
    }
    if (event.isARepeat || self.recordingAction < 0) {
        return;
    }
    NSUInteger flags = event.modifierFlags;
    unsigned int modifiers = ((flags & NSEventModifierFlagCommand) ? 256 : 0)
        | ((flags & NSEventModifierFlagShift) ? 512 : 0)
        | ((flags & NSEventModifierFlagOption) ? 2048 : 0)
        | ((flags & NSEventModifierFlagControl) ? 4096 : 0);
    NSString *character = [event charactersByApplyingModifiers:0] ?: event.charactersIgnoringModifiers;
    NSDictionary *candidate = @{@"key": @(event.keyCode), @"modifiers": @(modifiers), @"character": character.lowercaseString ?: @""};
    NSMutableArray *draft = [self.draft mutableCopy];
    draft[self.recordingAction] = candidate;
    NSString *error = shortcutsError(draft);
    if (error) {
        self.errorLabel.textColor = NSColor.systemRedColor;
        self.errorLabel.stringValue = error;
        return;
    }
    self.draft = draft;
    self.recordingAction = -1;
    self.errorLabel.textColor = NSColor.secondaryLabelColor;
    self.errorLabel.stringValue = @"点击「应用」保存；若快捷键被占用，会提示你重新设置。";
    [self refreshButtons];
}
- (void)restoreDefaults:(id)sender {
    self.draft = [defaultShortcuts() mutableCopy];
    self.recordingAction = -1;
    self.errorLabel.textColor = NSColor.secondaryLabelColor;
    self.errorLabel.stringValue = @"已恢复默认组合，点击「应用」后生效。";
    [self refreshButtons];
}
- (void)apply:(id)sender {
    self.recordingAction = -1;
    [self refreshButtons];
    NSString *error = shortcutsError(self.draft);
    if (error) {
        self.errorLabel.textColor = NSColor.systemRedColor;
        self.errorLabel.stringValue = error;
    } else if (self.callback) {
        self.callback(31);
    }
}
- (void)cancel:(id)sender {
    if (self.callback) {
        self.callback(32);
    }
}
- (BOOL)windowShouldClose:(NSWindow *)sender {
    [self cancel:nil];
    return NO;
}
@end

__attribute__((visibility("default")))
bool TexoShowShortcutSettings(TexoShortcutCallback callback) {
    if (!NSThread.isMainThread || !callback) {
        return false;
    }
    if (shortcutController) {
        [NSApp activateIgnoringOtherApps:YES];
        [shortcutController.panel makeKeyAndOrderFront:nil];
        return true;
    }
    shortcutController = [[TexoShortcutController alloc] init];
    shortcutController.callback = callback;
    shortcutController.recordingAction = -1;
    shortcutController.draft = [savedShortcuts() mutableCopy];
    NSPanel *panel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0, 0, 480, 274)
        styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
    panel.title = @"Texo 快捷键设置";
    panel.releasedWhenClosed = NO;
    panel.delegate = shortcutController;
    panel.collectionBehavior = NSWindowCollectionBehaviorMoveToActiveSpace;
    shortcutController.panel = panel;
    NSTextField *description = [NSTextField wrappingLabelWithString:@"点击「录制」，然后按下组合键。必须包含 ⌘、⌃ 或 ⌥；设置期间暂停 Texo 的全局快捷键。"];
    description.frame = NSMakeRect(20, 212, 440, 42);
    description.font = [NSFont systemFontOfSize:12];
    description.textColor = NSColor.secondaryLabelColor;
    [panel.contentView addSubview:description];
    NSMutableArray *buttons = [NSMutableArray array];
    NSArray *titles = @[@"截图识别", @"显示／收起结果"];
    for (NSUInteger action = 0; action < titles.count; action++) {
        CGFloat y = 166 - action * 46;
        NSTextField *label = [NSTextField labelWithString:titles[action]];
        label.frame = NSMakeRect(20, y, 140, 24);
        [panel.contentView addSubview:label];
        NSButton *button = [NSButton buttonWithTitle:@"" target:shortcutController action:@selector(beginRecording:)];
        button.frame = NSMakeRect(164, y - 4, 296, 32);
        button.bezelStyle = NSBezelStyleRounded;
        button.tag = action;
        button.accessibilityLabel = [@"录制" stringByAppendingString:titles[action]];
        [panel.contentView addSubview:button];
        [buttons addObject:button];
    }
    shortcutController.recordButtons = buttons;
    shortcutController.errorLabel = [NSTextField wrappingLabelWithString:@"快捷键只在点击「应用」后保存。"];
    shortcutController.errorLabel.frame = NSMakeRect(20, 64, 440, 42);
    shortcutController.errorLabel.font = [NSFont systemFontOfSize:12];
    shortcutController.errorLabel.textColor = NSColor.secondaryLabelColor;
    shortcutController.errorLabel.accessibilityLabel = @"快捷键设置状态";
    [panel.contentView addSubview:shortcutController.errorLabel];
    NSArray *buttonTitles = @[@"恢复默认", @"取消", @"应用"];
    SEL actions[] = {@selector(restoreDefaults:), @selector(cancel:), @selector(apply:)};
    CGFloat positions[] = {16, 276, 368};
    for (NSUInteger index = 0; index < buttonTitles.count; index++) {
        NSButton *button = [NSButton buttonWithTitle:buttonTitles[index] target:shortcutController action:actions[index]];
        button.frame = NSMakeRect(positions[index], 16, index == 0 ? 112 : 96, 32);
        button.bezelStyle = NSBezelStyleRounded;
        button.accessibilityLabel = buttonTitles[index];
        if (index == 1) button.keyEquivalent = @"\x1b";
        if (index == 2) button.keyEquivalent = @"\r";
        [panel.contentView addSubview:button];
    }
    [shortcutController refreshButtons];
    shortcutController.eventMonitor = [NSEvent addLocalMonitorForEventsMatchingMask:NSEventMaskKeyDown handler:^NSEvent *(NSEvent *event) {
        if (shortcutController.panel.isKeyWindow && shortcutController.recordingAction >= 0) {
            [shortcutController recordEvent:event];
            return nil;
        }
        return event;
    }];
    [panel center];
    [NSApp activateIgnoringOtherApps:YES];
    [panel makeKeyAndOrderFront:nil];
    return true;
}

__attribute__((visibility("default")))
bool TexoShortcutSettingsShown(void) {
    return NSThread.isMainThread && shortcutController.panel.visible;
}

__attribute__((visibility("default")))
void TexoShortcutSettingsSetError(const char *utf8) {
    if (NSThread.isMainThread && shortcutController) {
        shortcutController.errorLabel.textColor = NSColor.systemRedColor;
        shortcutController.errorLabel.stringValue = utf8 ? ([NSString stringWithUTF8String:utf8] ?: @"") : @"";
    }
}

__attribute__((visibility("default")))
int TexoGetDraftShortcutKey(int action) {
    return NSThread.isMainThread && shortcutController && action >= 0 && action <= 1 ? [shortcutController.draft[action][@"key"] intValue] : -1;
}

__attribute__((visibility("default")))
unsigned int TexoGetDraftShortcutModifiers(int action) {
    return NSThread.isMainThread && shortcutController && action >= 0 && action <= 1 ? [shortcutController.draft[action][@"modifiers"] unsignedIntValue] : 0;
}

__attribute__((visibility("default")))
const char *TexoGetDraftShortcutLabel(int action) {
    if (!NSThread.isMainThread || !shortcutController || action < 0 || action > 1) {
        return "";
    }
    labelSnapshot = shortcutLabel(shortcutController.draft[action]);
    return labelSnapshot.UTF8String;
}

__attribute__((visibility("default")))
bool TexoCommitShortcuts(void) {
    if (!NSThread.isMainThread || !shortcutController || shortcutsError(shortcutController.draft)) {
        return false;
    }
    [NSUserDefaults.standardUserDefaults setObject:shortcutController.draft forKey:@"TexoShortcuts"];
    TexoRefreshShortcutPresentation();
    return true;
}

__attribute__((visibility("default")))
void TexoShortcutSettingsClose(void) {
    if (!NSThread.isMainThread || !shortcutController) {
        return;
    }
    shortcutController.callback = NULL;
    if (shortcutController.eventMonitor) {
        [NSEvent removeMonitor:shortcutController.eventMonitor];
        shortcutController.eventMonitor = nil;
    }
    shortcutController.panel.delegate = nil;
    [shortcutController.panel close];
    shortcutController = nil;
}
