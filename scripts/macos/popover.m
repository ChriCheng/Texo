#import <AppKit/AppKit.h>
#include <stdbool.h>

extern void *TexoStatusItemButton(void);
extern int TexoGetCopyFormat(void);
extern void TexoSetCopyFormat(int format);
extern int TexoGetRecognitionMode(void);
extern void TexoSetRecognitionMode(int mode);
typedef void (*TexoPopoverCallback)(int);

@interface TexoPopoverView : NSView
@property(nonatomic, weak) NSPopover *popover;
@end

@implementation TexoPopoverView
- (void)drawRect:(NSRect)dirtyRect {
    [NSColor.whiteColor setFill];
    NSRectFill(dirtyRect);
}
- (void)cancelOperation:(id)sender {
    [self.popover performClose:sender];
}
@end

@interface TexoResultView : NSTextView
@property(nonatomic, weak) NSPopover *popover;
@end

@implementation TexoResultView
- (BOOL)performKeyEquivalent:(NSEvent *)event {
    if (self.window.firstResponder == self) {
        NSEventModifierFlags modifiers = event.modifierFlags & (NSEventModifierFlagCommand | NSEventModifierFlagShift | NSEventModifierFlagControl | NSEventModifierFlagOption);
        NSString *key = event.charactersIgnoringModifiers.lowercaseString;
        if (modifiers == NSEventModifierFlagCommand) {
            if ([key isEqualToString:@"a"]) { [self selectAll:nil]; return YES; }
            if ([key isEqualToString:@"c"]) { [self copy:nil]; return YES; }
            if ([key isEqualToString:@"x"]) { if (self.editable) [self cut:nil]; return YES; }
            if ([key isEqualToString:@"v"]) { if (self.editable) [self paste:nil]; return YES; }
            if ([key isEqualToString:@"z"]) {
                if (self.editable && self.undoManager.canUndo) [self.undoManager undo];
                return YES;
            }
        } else if (modifiers == (NSEventModifierFlagCommand | NSEventModifierFlagShift) && [key isEqualToString:@"z"]) {
            if (self.editable && self.undoManager.canRedo) [self.undoManager redo];
            return YES;
        }
    }
    return [super performKeyEquivalent:event];
}
- (void)cancelOperation:(id)sender {
    [self.popover performClose:sender];
}
@end

@interface TexoPopoverController : NSViewController <NSTextViewDelegate, NSPopoverDelegate>
@property(nonatomic, strong) NSPopover *popover;
@property(nonatomic, strong) NSImageView *preview;
@property(nonatomic, strong) NSTextField *previewHint;
@property(nonatomic, strong) TexoResultView *result;
@property(nonatomic, strong) NSTextField *status;
@property(nonatomic, strong) NSPopUpButton *mode;
@property(nonatomic, strong) NSPopUpButton *format;
@property(nonatomic, strong) NSButton *resultCopyButton;
@property(nonatomic, strong) NSButton *pptCopyButton;
@property(nonatomic, strong) NSArray<NSButton *> *inputButtons;
@property(nonatomic, copy) NSString *resultSnapshot;
@property(nonatomic, assign) TexoPopoverCallback callback;
@property(nonatomic, assign) BOOL busy;
@property(nonatomic, assign) int resultMode;
- (void)refreshControls;
- (void)focusResult;
@end

@implementation TexoPopoverController
- (NSTextField *)label:(NSString *)title frame:(NSRect)frame size:(CGFloat)size {
    NSTextField *label = [NSTextField labelWithString:title];
    label.frame = frame;
    label.font = [NSFont systemFontOfSize:size];
    label.textColor = NSColor.labelColor;
    [self.view addSubview:label];
    return label;
}
- (NSButton *)button:(NSString *)title frame:(NSRect)frame event:(NSInteger)event {
    NSButton *button = [NSButton buttonWithTitle:title target:self action:@selector(selected:)];
    button.frame = frame;
    button.bezelStyle = NSBezelStyleRounded;
    button.tag = event;
    button.accessibilityLabel = title;
    [self.view addSubview:button];
    return button;
}
- (void)loadView {
    self.view = [[TexoPopoverView alloc] initWithFrame:NSMakeRect(0, 0, 760, 430)];
    [self label:@"截图预览" frame:NSMakeRect(20, 394, 340, 22) size:13];
    [self label:@"识别结果" frame:NSMakeRect(392, 394, 348, 22) size:13];

    self.preview = [[NSImageView alloc] initWithFrame:NSMakeRect(20, 96, 340, 288)];
    self.preview.imageScaling = NSImageScaleProportionallyUpOrDown;
    self.preview.imageAlignment = NSImageAlignCenter;
    self.preview.accessibilityLabel = @"截图预览";
    [self.view addSubview:self.preview];
    self.previewHint = [self label:@"选择图片、截图或识别剪贴板" frame:NSMakeRect(28, 228, 324, 22) size:14];
    self.previewHint.alignment = NSTextAlignmentCenter;
    self.previewHint.textColor = NSColor.secondaryLabelColor;

    NSScrollView *scroll = [[NSScrollView alloc] initWithFrame:NSMakeRect(392, 96, 348, 288)];
    scroll.borderType = NSNoBorder;
    scroll.hasVerticalScroller = YES;
    scroll.drawsBackground = NO;
    self.result = [[TexoResultView alloc] initWithFrame:scroll.contentView.bounds];
    self.result.font = [NSFont monospacedSystemFontOfSize:15 weight:NSFontWeightRegular];
    self.result.textColor = NSColor.textColor;
    self.result.insertionPointColor = NSColor.textColor;
    self.result.drawsBackground = NO;
    self.result.richText = NO;
    self.result.allowsUndo = YES;
    self.result.automaticQuoteSubstitutionEnabled = NO;
    self.result.automaticDashSubstitutionEnabled = NO;
    self.result.automaticTextReplacementEnabled = NO;
    self.result.automaticSpellingCorrectionEnabled = NO;
    self.result.textContainerInset = NSMakeSize(8, 8);
    self.result.verticallyResizable = YES;
    self.result.horizontallyResizable = NO;
    self.result.autoresizingMask = NSViewWidthSizable;
    self.result.textContainer.widthTracksTextView = YES;
    self.result.delegate = self;
    self.result.accessibilityLabel = @"可编辑的识别结果";
    scroll.documentView = self.result;
    [self.view addSubview:scroll];

    NSButton *choose = [self button:@"选择图片" frame:NSMakeRect(16, 52, 108, 32) event:6];
    NSButton *capture = [self button:@"截图 ⌘L" frame:NSMakeRect(130, 52, 108, 32) event:2];
    NSButton *clipboard = [self button:@"识别剪贴板" frame:NSMakeRect(244, 52, 120, 32) event:3];
    self.inputButtons = @[choose, capture, clipboard];
    self.resultCopyButton = [self button:@"复制公式" frame:NSMakeRect(628, 52, 116, 32) event:7];
    self.resultCopyButton.toolTip = @"复制当前编辑后的识别结果。";
    self.pptCopyButton = [self button:@"复制到 PPT" frame:NSMakeRect(500, 52, 124, 32) event:9];
    self.pptCopyButton.toolTip = @"将当前编辑后的识别结果复制为适合 PowerPoint 粘贴的内容。";

    self.mode = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(16, 10, 150, 30) pullsDown:NO];
    [self.mode addItemsWithTitles:@[@"中文与公式", @"公式"]];
    [self.mode selectItemAtIndex:TexoGetRecognitionMode()];
    self.resultMode = (int)self.mode.indexOfSelectedItem;
    self.mode.target = self;
    self.mode.action = @selector(modeChanged:);
    self.mode.accessibilityLabel = @"识别模式";
    [self.view addSubview:self.mode];
    [self label:@"复制格式" frame:NSMakeRect(184, 15, 64, 22) size:12];
    self.format = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(248, 10, 116, 30) pullsDown:NO];
    [self.format addItemsWithTitles:@[@"LaTeX", @"$LaTeX$", @"$$LaTeX$$"]];
    [self.format selectItemAtIndex:TexoGetCopyFormat()];
    self.format.target = self;
    self.format.action = @selector(formatChanged:);
    self.format.accessibilityLabel = @"公式复制格式";
    self.format.toolTip = @"选择纯公式的显示格式；普通复制使用相同的 LaTeX 文本。中文与公式混排保留 Markdown，PPT 复制转换为可编辑公式。";
    [self.view addSubview:self.format];
    self.status = [self label:@"选择图片，或按 ⌘L 截图识别" frame:NSMakeRect(392, 15, 348, 22) size:12];
    self.status.lineBreakMode = NSLineBreakByTruncatingTail;
    self.status.accessibilityLabel = @"识别状态";
    [self refreshControls];
}
- (void)selected:(NSButton *)sender {
    if (self.callback) {
        self.callback((int)sender.tag);
    }
}
- (void)modeChanged:(id)sender {
    TexoSetRecognitionMode((int)self.mode.indexOfSelectedItem);
    if (self.callback) {
        self.callback(8);
    }
}
- (void)formatChanged:(id)sender {
    int format = (int)self.format.indexOfSelectedItem;
    TexoSetCopyFormat(format);
    if (self.callback) {
        self.callback(10 + format);
    }
}
- (void)textDidChange:(NSNotification *)notification {
    [self refreshControls];
}
- (void)focusResult {
    if (self.popover.shown) {
        NSWindow *window = self.view.window;
        [window makeKeyAndOrderFront:nil];
        [window makeFirstResponder:self.result];
    }
}
- (void)popoverDidShow:(NSNotification *)notification {
    // The popover creates and animates its own window; focus it once ready.
    [self focusResult];
}
- (void)refreshControls {
    for (NSButton *button in self.inputButtons) {
        button.enabled = !self.busy;
    }
    self.mode.enabled = !self.busy;
    self.format.enabled = !self.busy && self.resultMode == 1;
    self.result.editable = !self.busy;
    self.resultCopyButton.enabled = !self.busy && [self.result.string stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet].length > 0;
    self.pptCopyButton.enabled = self.resultCopyButton.enabled;
}
@end

static TexoPopoverController *popoverController;

__attribute__((visibility("default")))
bool TexoInstallPopover(TexoPopoverCallback callback) {
    if (!NSThread.isMainThread || !callback || popoverController || !TexoStatusItemButton()) {
        return false;
    }
    popoverController = [[TexoPopoverController alloc] init];
    popoverController.callback = callback;
    NSPopover *popover = [[NSPopover alloc] init];
    popover.behavior = NSPopoverBehaviorTransient;
    popover.animates = YES;
    popover.appearance = [NSAppearance appearanceNamed:NSAppearanceNameAqua];
    popover.contentSize = NSMakeSize(760, 430);
    popover.contentViewController = popoverController;
    popover.delegate = popoverController;
    popoverController.popover = popover;
    ((TexoPopoverView *)popoverController.view).popover = popover;
    popoverController.result.popover = popover;
    return true;
}

__attribute__((visibility("default")))
void TexoShowPopover(void) {
    if (!NSThread.isMainThread || !popoverController) {
        return;
    }
    NSView *button = (__bridge NSView *)TexoStatusItemButton();
    if (button) {
        [NSApp activateIgnoringOtherApps:YES];
        [popoverController.popover showRelativeToRect:button.bounds ofView:button preferredEdge:NSRectEdgeMinY];
        [popoverController focusResult];
    }
}

__attribute__((visibility("default")))
void TexoHidePopover(bool immediately) {
    if (NSThread.isMainThread) {
        // Only capture skips closing animation, so no fading UI enters the screenshot.
        popoverController.popover.animates = !immediately;
        [popoverController.popover close];
        popoverController.popover.animates = YES;
    }
}

__attribute__((visibility("default")))
bool TexoPopoverShown(void) {
    return NSThread.isMainThread && popoverController.popover.shown;
}

__attribute__((visibility("default")))
void TexoPopoverSetImage(const void *png, size_t length) {
    if (!NSThread.isMainThread || !popoverController) {
        return;
    }
    NSData *data = png && length ? [NSData dataWithBytes:png length:length] : nil;
    popoverController.preview.image = data ? [[NSImage alloc] initWithData:data] : nil;
    popoverController.previewHint.hidden = popoverController.preview.image != nil;
}

__attribute__((visibility("default")))
void TexoPopoverSetResult(const char *utf8) {
    if (NSThread.isMainThread && popoverController) {
        NSTextView *result = popoverController.result;
        NSString *text = utf8 ? ([NSString stringWithUTF8String:utf8] ?: @"") : @"";
        NSRange range = NSMakeRange(0, result.string.length);
        // OCR updates arrive while user editing is disabled.
        BOOL editable = result.editable;
        result.editable = YES;
        if (![result.string isEqualToString:text] && [result shouldChangeTextInRange:range replacementString:text]) {
            NSAttributedString *replacement = [[NSAttributedString alloc] initWithString:text attributes:result.typingAttributes];
            [result.textStorage replaceCharactersInRange:range withAttributedString:replacement];
            [result didChangeText];
        }
        result.editable = editable;
        [popoverController refreshControls];
    }
}

__attribute__((visibility("default")))
void TexoPopoverResetUndo(void) {
    if (NSThread.isMainThread && popoverController) {
        [popoverController.result breakUndoCoalescing];
        [popoverController.result.undoManager removeAllActions];
    }
}

__attribute__((visibility("default")))
void TexoPopoverSetCaptureShortcut(const char *label) {
    if (NSThread.isMainThread && popoverController) {
        NSString *shortcut = label ? [NSString stringWithUTF8String:label] : nil;
        NSButton *button = popoverController.inputButtons[1];
        button.title = [@"截图 " stringByAppendingString:shortcut.length ? shortcut : @"⌘L"];
        button.accessibilityLabel = button.title;
        button.toolTip = button.title;
    }
}

__attribute__((visibility("default")))
const char *TexoPopoverGetResult(void) {
    if (!NSThread.isMainThread || !popoverController) {
        return "";
    }
    popoverController.resultSnapshot = popoverController.result.string;
    return popoverController.resultSnapshot.UTF8String;
}

__attribute__((visibility("default")))
void TexoPopoverSetStatus(const char *utf8) {
    if (NSThread.isMainThread && popoverController) {
        popoverController.status.stringValue = utf8 ? ([NSString stringWithUTF8String:utf8] ?: @"") : @"";
        popoverController.status.toolTip = popoverController.status.stringValue;
    }
}

__attribute__((visibility("default")))
void TexoPopoverSetBusy(bool busy) {
    if (NSThread.isMainThread && popoverController) {
        popoverController.busy = busy;
        [popoverController refreshControls];
    }
}

__attribute__((visibility("default")))
int TexoPopoverGetMode(void) {
    return NSThread.isMainThread && popoverController ? (int)popoverController.mode.indexOfSelectedItem : 0;
}

__attribute__((visibility("default")))
void TexoPopoverSetMode(int mode) {
    if (NSThread.isMainThread && popoverController && (mode == 0 || mode == 1)) {
        TexoSetRecognitionMode(mode);
        [popoverController.mode selectItemAtIndex:mode];
    }
}

__attribute__((visibility("default")))
void TexoPopoverSetResultMode(int mode) {
    if (NSThread.isMainThread && popoverController && (mode == 0 || mode == 1)) {
        popoverController.resultMode = mode;
        [popoverController refreshControls];
    }
}

__attribute__((visibility("default")))
int TexoPopoverGetFormat(void) {
    return NSThread.isMainThread && popoverController ? TexoGetCopyFormat() : 2;
}

__attribute__((visibility("default")))
void TexoPopoverSetFormat(int format) {
    if (NSThread.isMainThread && popoverController && format >= 0 && format <= 2) {
        TexoSetCopyFormat(format);
        [popoverController.format selectItemAtIndex:format];
    }
}

__attribute__((visibility("default")))
void TexoRemovePopover(void) {
    if (!NSThread.isMainThread || !popoverController) {
        return;
    }
    popoverController.callback = NULL;
    popoverController.result.delegate = nil;
    popoverController.popover.delegate = nil;
    popoverController.popover.animates = NO;
    [popoverController.popover close];
    popoverController.popover.contentViewController = nil;
    popoverController.popover = nil;
    popoverController = nil;
}
