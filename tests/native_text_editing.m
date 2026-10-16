#import <AppKit/AppKit.h>
#include <dlfcn.h>
#include <math.h>
#import "../scripts/macos/popover.m"

void *TexoStatusItemButton(void) { return NULL; }
int TexoGetCopyFormat(void) { return 2; }
void TexoSetCopyFormat(int format) { }
int TexoGetCopyMode(void) { return 0; }
int TexoGetRecognitionMode(void) { return 1; }
void TexoSetRecognitionMode(int mode) { }

@interface ClipboardSpyView : TexoResultView
@property int copies;
@property int cuts;
@property int pastes;
@end
@implementation ClipboardSpyView
- (void)copy:(id)sender { self.copies++; }
- (void)cut:(id)sender { self.cuts++; }
- (void)paste:(id)sender { self.pastes++; }
@end

static int failures;
static void check(BOOL condition, const char *message) {
    fprintf(condition ? stdout : stderr, "%s %s\n", condition ? "PASS" : "FAIL", message);
    if (!condition) failures++;
}
static NSEvent *key(NSString *character, NSEventModifierFlags modifiers, NSWindow *window) {
    return [NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:modifiers
                         timestamp:0 windowNumber:window.windowNumber context:nil characters:character
       charactersIgnoringModifiers:character isARepeat:NO keyCode:0];
}
static void finishUndoGroup(NSTextView *view) {
    [view breakUndoCoalescing];
    [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.01]];
}

int main(void) {
    @autoreleasepool {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
        popoverController = [[TexoPopoverController alloc] init];
        NSWindow *window = [[NSWindow alloc] initWithContentRect:NSMakeRect(-10000, -10000, 760, 430)
                                                    styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
        window.releasedWhenClosed = NO;
        window.contentView = popoverController.view;
        TexoResultView *view = popoverController.result;
        [window makeFirstResponder:view];
        TexoPopoverSetResult("abc");
        NSFont *font = [view.textStorage attribute:NSFontAttributeName atIndex:0 effectiveRange:NULL];
        check(font && fabs(font.pointSize - 15) < 0.01 && (font.fontDescriptor.symbolicTraits & NSFontMonoSpaceTrait), "programmatic result preserves editor font");
        [view setSelectedRange:NSMakeRange(1, 0)];
        BOOL handled = [view performKeyEquivalent:key(@"a", NSEventModifierFlagCommand, window)];
        check(handled && NSEqualRanges(view.selectedRange, NSMakeRange(0, 3)), "focused Command-A selects all");
        check(view.allowsUndo, "text editing opts into undo");
        [view.undoManager removeAllActions];
        [view setSelectedRange:NSMakeRange(view.string.length, 0)];
        [view insertText:@"d" replacementRange:NSMakeRange(NSNotFound, 0)];
        finishUndoGroup(view);
        [view performKeyEquivalent:key(@"z", NSEventModifierFlagCommand, window)];
        check([view.string isEqualToString:@"abc"], "focused Command-Z undoes typing");
        [view performKeyEquivalent:key(@"z", NSEventModifierFlagCommand | NSEventModifierFlagShift, window)];
        check([view.string isEqualToString:@"abcd"], "focused Command-Shift-Z redoes typing");

        [view.undoManager removeAllActions];
        TexoPopoverSetResult("$$abcd$$");
        finishUndoGroup(view);
        [view performKeyEquivalent:key(@"z", NSEventModifierFlagCommand, window)];
        check([view.string isEqualToString:@"abcd"], "format replacement preserves edits and is undoable");
        void (*resetUndo)(void) = dlsym(RTLD_DEFAULT, "TexoPopoverResetUndo");
        check(resetUndo != NULL, "new OCR result can reset undo history");
        if (resetUndo) {
            TexoPopoverSetBusy(true);
            TexoPopoverSetResult("new OCR");
            resetUndo();
            TexoPopoverSetBusy(false);
            check([view.string isEqualToString:@"new OCR"] && !view.undoManager.canUndo, "new OCR baseline replaces text while busy and clears undo");
        }
        NSUInteger removedButtons = 0;
        for (NSView *subview in popoverController.view.subviews) {
            if ([subview isKindOfClass:NSButton.class] && subview.tag == 9) removedButtons++;
        }
        check(popoverController.resultCopyButton.tag == 7 && popoverController.resultCopyButton.enabled && removedButtons == 0,
              "one result copy button replaces the separate PPT button");
        check([popoverController.resultCopyButton.title isEqualToString:@"复制结果"], "copy caption initializes from the saved normal mode");
        TexoPopoverSetCopyMode(1);
        check([popoverController.resultCopyButton.title isEqualToString:@"复制到 PPT"] &&
              [popoverController.resultCopyButton.accessibilityLabel isEqualToString:@"复制到 PPT"] &&
              [popoverController.resultCopyButton.toolTip containsString:@"PowerPoint"], "PPT mode updates the copy caption and accessibility");
        TexoPopoverSetCopyMode(-1);
        TexoPopoverSetCopyMode(2);
        check([popoverController.resultCopyButton.title isEqualToString:@"复制到 PPT"], "invalid copy modes leave the caption unchanged");
        TexoPopoverSetCopyMode(0);
        check([popoverController.resultCopyButton.title isEqualToString:@"复制结果"] &&
              ![popoverController.resultCopyButton.toolTip containsString:@"PowerPoint"], "normal mode restores the copy caption and tooltip");
        TexoPopoverSetBusy(true);
        check(!popoverController.resultCopyButton.enabled, "copy button is disabled while busy");
        TexoPopoverSetBusy(false);
        TexoPopoverSetResult("");
        check(!popoverController.resultCopyButton.enabled, "copy button is disabled for an empty result");
        TexoPopoverSetCaptureShortcut("⌃⌥K");
        check([popoverController.inputButtons[1].title isEqualToString:@"截图 ⌃⌥K"] &&
              [popoverController.inputButtons[1].accessibilityLabel isEqualToString:@"截图 ⌃⌥K"], "capture button and accessibility reflect the configured shortcut");

        ClipboardSpyView *spy = [[ClipboardSpyView alloc] initWithFrame:NSMakeRect(0, 0, 100, 50)];
        [window.contentView addSubview:spy];
        [window makeFirstResponder:spy];
        for (NSString *character in @[@"c", @"x", @"v"]) {
            [spy performKeyEquivalent:key(character, NSEventModifierFlagCommand, window)];
        }
        check(spy.copies == 1 && spy.cuts == 1 && spy.pastes == 1, "focused standard clipboard commands dispatch to text view");
        [window makeFirstResponder:view];
        for (NSString *character in @[@"a", @"c", @"x", @"v", @"z"]) {
            [spy performKeyEquivalent:key(character, NSEventModifierFlagCommand, window)];
        }
        check(spy.copies == 1 && spy.cuts == 1 && spy.pastes == 1, "unfocused editor leaves commands untouched");
        [window close];
        popoverController = nil;
    }
    return failures ? 1 : 0;
}
