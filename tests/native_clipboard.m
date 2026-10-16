#import <AppKit/AppKit.h>
#import "../scripts/macos/clipboard.m"

int main(void) {
    @autoreleasepool {
        NSPasteboard *board = [NSPasteboard pasteboardWithUniqueName];
        [board clearContents];
        if (![board setString:@"previous" forType:NSPasteboardTypeString]) return 1;
        if (copyOfficeToPasteboard(board, @"中文 $x$", @"")) return 2;
        if (![[board stringForType:NSPasteboardTypeString] isEqualToString:@"previous"]) return 3;
        NSString *xml = @"<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi></math>";
        NSString *html = [@"<p>中文" stringByAppendingFormat:@"%@</p>", xml];
        if (!copyOfficeToPasteboard(board, @"中文 $x$", html)) return 4;
        if ([board.types containsObject:NSPasteboardTypeString]) return 5;
        if (![[board stringForType:NSPasteboardTypeHTML] isEqualToString:html]) return 6;
        if (![[board stringForType:@"com.chricheng.texo.source"] isEqualToString:@"中文 $x$"]) {
            fputs("FAIL private source text is missing from the Office payload\n", stderr);
            return 7;
        }
        if (copyOfficeToPasteboard(board, @"", html)) return 8;
        if (![[board stringForType:NSPasteboardTypeHTML] isEqualToString:html] ||
            ![[board stringForType:@"com.chricheng.texo.source"] isEqualToString:@"中文 $x$"]) return 9;
        [board releaseGlobally];
        puts("PASS private pasteboard HTML with MathML, source text and failed-input preservation");
    }
    return 0;
}
