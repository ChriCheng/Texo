#import <AppKit/AppKit.h>
#include <stdbool.h>

static bool copyOfficeToPasteboard(NSPasteboard *pasteboard, NSString *html) {
    if (!html.length) {
        return false;
    }
    NSPasteboardItem *item = [[NSPasteboardItem alloc] init];
    // A plain LaTeX fallback lets PowerPoint bypass the MathML importer.
    if (![item setString:html forType:NSPasteboardTypeHTML]) {
        return false;
    }
    NSMutableArray<NSPasteboardItem *> *previous = [NSMutableArray array];
    for (NSPasteboardItem *old in pasteboard.pasteboardItems) {
        NSPasteboardItem *saved = [[NSPasteboardItem alloc] init];
        for (NSPasteboardType type in old.types) {
            NSData *data = [old dataForType:type];
            // Do not discard promised data that cannot yet be materialized.
            if (!data || ![saved setData:data forType:type]) {
                return false;
            }
        }
        [previous addObject:saved];
    }
    [pasteboard clearContents];
    if ([pasteboard writeObjects:@[item]]) {
        return true;
    }
    [pasteboard clearContents];
    if (previous.count) {
        [pasteboard writeObjects:previous];
    }
    return false;
}

__attribute__((visibility("default")))
bool TexoCopyOffice(const char *html) {
    if (!NSThread.isMainThread || !html) {
        return false;
    }
    return copyOfficeToPasteboard(NSPasteboard.generalPasteboard, [NSString stringWithUTF8String:html]);
}
