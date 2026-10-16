# macOS OCR workflow

## Requested behavior

- Recognize the three supplied formula images and distinguish renderer incompatibility from cropped input. Convert verified equivalent command aliases for Obsidian/MathJax; preserve mathematical and text content.
- Let the user select plain LaTeX, `$LaTeX$`, or `$$LaTeX$$` when copying. The native app defaults to `$$LaTeX$$`. Copied text and CLI output have no trailing newline.
- Read image data from the clipboard and recognize it through the same model path as selected files.
- Capture a temporary screen region and recognize it. Cancellation preserves the previous result, and temporary image files are removed.
- Register global Command-L while Texo is running, as explicitly confirmed by the user. It triggers region capture even while another application is in front. Registration failures are visible; quitting Texo releases the shortcut.
- Keep the UI responsive and prevent overlapping recognition/capture requests. No training or upload of user images is required.
- Extend recognition to Chinese text mixed with formulas, as explicitly selected
  by the user. Preserve text/formula reading order in a single-column screenshot.
  Use Markdown with inline and display math delimiters for mixed output; do not
  wrap the entire Chinese result in math. Keep pure formula mode and its three
  copy formats available. Both modes work for files, clipboard images and captures.
- Package the working local OCR as Texo.app, install it in an Applications folder
  and verify it appears in Spotlight search. Open without a terminal window,
  preserve the existing recognition/clipboard/capture workflows, raise the
  existing interface on repeated launch and release the shortcuts when quitting.
  Make the local runtime dependency and app-specific screen recording grant clear.
- Keep Texo.app resident in the menu bar without a Dock icon. Present a white
  native NSPopover with image preview on the left and editable result on the
  right. Left-clicking or right-clicking the icon opens its menu; the show/hide
  menu item or global Command-Shift-semicolon toggles the popover. Escape or
  clicking outside it hides only the popover. Keep the terminal-launched
  Tk window as a fallback, where closing the window still quits that instance.
- Command-L hides the popover before interactive region selection. File,
  clipboard and screenshot recognition keep the popover hidden during OCR by
  default. Success displays the input image and completed result and
  automatically copies the chosen format without a trailing newline.
  The user can show progress using the menu or Command-Shift-semicolon while OCR
  is running. Showing or hiding the popover must not cancel recognition. Failure
  and cancellation preserve the existing clipboard; cancellation also preserves
  the previous recognition result.
- Put recognition mode and the three pure-formula copy formats in the menu and
  persist their selections across restarts. Mixed output remains Markdown with
  prose outside math delimiters, regardless of the pure-formula format selection.
  If mixed recognition returns only one formula and no prose, treat that result
  as pure formula output and apply the selected format, including the initial
  display-math default.
- Use a transparent monochrome template icon derived from the original logo's
  four corners and outlined formula. During recognition show a pie-style activity
  indicator reflecting completed phases, with rotating indeterminate activity
  during unknown-length phases rather than invented percentages. Restore the
  normal icon on completion, failure or cancellation.
- Provide login startup and quitting in the icon's menu. Login
  startup opens the app in the background with the popover hidden, using only
  Texo's per-user LaunchAgent and no KeepAlive. Quitting leaves the next-login
  setting intact; disabling startup does not terminate the running app. Report
  startup changes that fail without overwriting unrelated entries.
- Preserve the dependency on this checkout, its virtual environment, models and
  base Python installation. Rebuilding the ad-hoc-signed launcher can require
  screen-recording authorization again. Shortcut rebinding remains future work.
- Maintain the user's personal macOS version on `ChriCheng/Texo:main`.
  Develop on feature branches such as `codex/macos-local-ocr`, then merge tested
  changes into the fork's `main`. Review upstream updates from `alephpi/Texo`
  and merge them only when the user chooses; do not configure automatic upstream
  synchronization or push to the upstream repository.

## Verification

Test the public normalization and copy-format interfaces, CLI bytes, real OCR with file and image inputs, desktop clipboard/display/error recovery, screenshot cancellation and cleanup, and macOS hotkey registration/dispatch. Separately report native region selection or hardware keyboard checks that require user interaction.

Verify literal Chinese/English/numeric text and a self-rendered screenshot with
Chinese on both sides of an inline formula plus a display formula. Exercise mode
switching and Markdown copying without a trailing newline. Report model errors
and missing native tools/model files instead of silently dropping content.

Verify real LaunchServices launch, native app identity, one instance on repeated
open, reopening a hidden popover, recognition and clipboard output in the app,
and normal application quit. Check Spotlight metadata for the installed path;
report app-specific screenshot authorization separately.

Verify icon/shortcut toggling, Escape/outside-click dismissal, editable result
and copy formats in the native popover, both mouse buttons opening the menu,
persisted mode/format selections and the initial display-math default. Verify
capture before presentation, default hidden OCR for files/clipboard/captures,
completion display and automatic copy bytes, optional progress inspection and
activity-icon recovery. Check formula-only output from mixed recognition uses
the chosen pure-formula wrapper while prose-containing Markdown stays intact. Confirm
failure/cancellation do not replace the clipboard. Verify login entry
creation/removal, background startup, no KeepAlive, and preservation of unrelated startup entries. Distinguish
a launchctl/background-launch check from an actual logout/login test.

Review the menu, activity and automatic-copy update against
`1c2784b3eba364e6b4251d4ceb54207bb2beeab1` before committing.
