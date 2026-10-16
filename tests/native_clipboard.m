#import <AppKit/AppKit.h>
#import "../scripts/macos/clipboard.m"

int main(void) {
    @autoreleasepool {
        NSPasteboard *board = [NSPasteboard pasteboardWithUniqueName];
        [board clearContents];
        if (![board setString:@"previous" forType:NSPasteboardTypeString]) return 1;
        if (copyOfficeToPasteboard(board, @"")) return 2;
        if (![[board stringForType:NSPasteboardTypeString] isEqualToString:@"previous"]) return 3;
        NSString *xml = @"<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi></math>";
        NSString *html = [@"<p>中文" stringByAppendingFormat:@"%@</p>", xml];
        if (!copyOfficeToPasteboard(board, html)) return 4;
        if ([board.types containsObject:NSPasteboardTypeString]) return 5;
        if (![[board stringForType:NSPasteboardTypeHTML] isEqualToString:html]) return 6;
        [board releaseGlobally];
        puts("PASS private pasteboard HTML with MathML and failed-input preservation");
    }
    return 0;
}
