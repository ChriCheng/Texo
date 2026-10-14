#import <AppKit/AppKit.h>
#include <stdbool.h>

typedef void (*TexoStatusCallback)(int);

@interface TexoStatusController : NSObject
@property(nonatomic, strong) NSStatusItem *item;
@property(nonatomic, strong) NSMenu *menu;
@property(nonatomic, strong) NSMenuItem *loginItem;
@property(nonatomic, assign) TexoStatusCallback callback;
@end

@implementation TexoStatusController
- (void)clicked:(id)sender {
    NSEvent *event = NSApp.currentEvent;
    if (event.type == NSEventTypeRightMouseUp) {
        [NSMenu popUpContextMenu:self.menu withEvent:event forView:self.item.button];
    } else if (self.callback) {
        self.callback(1);
    }
}

- (void)selected:(NSMenuItem *)sender {
    if (self.callback) {
        self.callback((int)sender.tag);
    }
}
@end

static TexoStatusController *controller;

__attribute__((visibility("default")))
void *TexoStatusItemButton(void) {
    if (!NSThread.isMainThread) {
        return NULL;
    }
    return (__bridge void *)controller.item.button;
}

__attribute__((visibility("default")))
bool TexoInstallStatusItem(TexoStatusCallback callback) {
    if (!NSThread.isMainThread || !callback || controller) {
        return false;
    }
    [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    controller = [[TexoStatusController alloc] init];
    controller.callback = callback;
    controller.item = [NSStatusBar.systemStatusBar statusItemWithLength:NSSquareStatusItemLength];
    NSStatusBarButton *button = controller.item.button;
    NSImage *image = [NSImage imageWithSystemSymbolName:@"doc.text.viewfinder" accessibilityDescription:@"Texo"];
    image.template = YES;
    image.size = NSMakeSize(18, 18);
    button.image = image;
    button.toolTip = @"Texo · ⌘⇧; 显示／收起结果，⌘L 截图，右键显示菜单";
    button.accessibilityLabel = @"Texo";
    button.target = controller;
    button.action = @selector(clicked:);
    [button sendActionOn:NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp];

    controller.menu = [[NSMenu alloc] initWithTitle:@"Texo"];
    NSArray<NSString *> *titles = @[@"显示／收起结果 ⌘⇧;", @"截图识别 ⌘L", @"识别剪贴板", @"登录时自动启动", @"退出 Texo"];
    for (NSUInteger index = 0; index < titles.count; index++) {
        if (index == 3 || index == 4) {
            [controller.menu addItem:NSMenuItem.separatorItem];
        }
        NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:titles[index] action:@selector(selected:) keyEquivalent:@""];
        item.tag = index + 1;
        item.target = controller;
        [controller.menu addItem:item];
        if (index == 3) {
            controller.loginItem = item;
        }
    }
    return true;
}

__attribute__((visibility("default")))
void TexoSetLoginEnabled(bool enabled) {
    if (NSThread.isMainThread) {
        controller.loginItem.state = enabled ? NSControlStateValueOn : NSControlStateValueOff;
    }
}

__attribute__((visibility("default")))
void TexoActivateApplication(void) {
    if (NSThread.isMainThread) {
        [NSApp activateIgnoringOtherApps:YES];
    }
}

__attribute__((visibility("default")))
void TexoRemoveStatusItem(void) {
    if (!NSThread.isMainThread || !controller) {
        return;
    }
    controller.callback = NULL;
    controller.item.button.target = nil;
    [NSStatusBar.systemStatusBar removeStatusItem:controller.item];
    controller = nil;
}
