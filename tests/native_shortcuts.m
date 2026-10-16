#import "../scripts/macos/shortcuts.m"
#include <assert.h>

void TexoRefreshShortcutPresentation(void) { }

int main(void) {
    @autoreleasepool {
        // Exercise validation and labels without creating UI or reading user defaults.
        NSArray *defaults = defaultShortcuts();
        assert(shortcutsError(defaults) == nil);
        assert([defaults[0][@"key"] intValue] == 37 && [defaults[0][@"modifiers"] intValue] == 256);
        assert([defaults[1][@"key"] intValue] == 41 && [defaults[1][@"modifiers"] intValue] == 768);
        assert([shortcutLabel(defaults[0]) isEqualToString:@"⌘L"]);
        assert([shortcutLabel(defaults[1]) isEqualToString:@"⌘⇧;"]);

        for (NSNumber *modifiers in @[@0, @512, @1, @(-1)]) {
            assert(shortcutError(@{@"key": @37, @"modifiers": modifiers, @"character": @"l"}));
        }
        for (NSNumber *key in @[@(-1), @53, @55, @63, @127]) {
            assert(shortcutError(@{@"key": key, @"modifiers": @256, @"character": @"l"}));
        }
        for (NSString *character in @[@"a", @"c", @"x", @"v", @"z", @"q", @"w", @"h", @"m", @"s", @"f", @"p", @"n", @"o"]) {
            for (NSNumber *modifiers in @[@256, @768]) {
                assert(shortcutError(@{@"key": @0, @"modifiers": modifiers, @"character": character}));
            }
        }
        assert(shortcutError(@{@"key": @8, @"modifiers": @4352, @"character": @"c"}) == nil);
        assert(shortcutError(@{@"key": @8, @"modifiers": @2304, @"character": @"c"}) == nil);
        assert(shortcutError(@{@"key": @37, @"modifiers": @256, @"character": @""}));
        assert(shortcutError((id)@"invalid"));
        assert(shortcutsError(nil));
        assert(shortcutsError(@[defaults[0]]));
        assert(shortcutsError(@[defaults[0], defaults[0]]));
        NSDictionary *custom = @{@"key": @40, @"modifiers": @2304, @"character": @"k"};
        assert(shortcutsError(@[custom, defaults[1]]) == nil);
        assert([shortcutLabel(custom) isEqualToString:@"⌥⌘K"]);
        assert([shortcutLabel(@{@"key": @49, @"modifiers": @256, @"character": @" "}) isEqualToString:@"⌘空格"]);
        assert([shortcutLabel(@{@"key": @32, @"modifiers": @256, @"character": @"u"}) isEqualToString:@"⌘U"]);
        assert([shortcutLabel(@{@"key": @123, @"modifiers": @4096, @"character": @"←"}) isEqualToString:@"⌃←"]);
        unichar functionKey = NSF6FunctionKey;
        NSString *functionCharacter = [NSString stringWithCharacters:&functionKey length:1];
        assert([shortcutLabel(@{@"key": @97, @"modifiers": @2048, @"character": functionCharacter}) isEqualToString:@"⌥F6"]);

        assert(TexoGetShortcutKey(-1) == -1 && TexoGetShortcutModifiers(2) == 0);
        assert(strcmp(TexoGetShortcutLabel(2), "") == 0);
        assert(TexoGetDraftShortcutKey(0) == -1 && TexoGetDraftShortcutModifiers(1) == 0);
        puts("PASS: native shortcut defaults, validation, duplicate rejection, labels, and inactive getters; no GUI or user preferences accessed");
    }
    return 0;
}
