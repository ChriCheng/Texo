# macOS OCR workflow

## Requested behavior

- Recognize the three supplied formula images and distinguish renderer incompatibility from cropped input. Convert verified equivalent command aliases for Obsidian/MathJax; preserve mathematical and text content.
- Let the user select plain LaTeX, `$LaTeX$`, or `$$LaTeX$$` when copying. Copied text and CLI output have no trailing newline.
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
  right. Clicking its icon or global Command-Shift-semicolon toggles the popover;
  Escape or clicking outside it hides only the popover. Keep the terminal-launched
  Tk window as a fallback, where closing the window still quits that instance.
- Command-L hides the popover before interactive region selection, then shows
  the captured image and recognition progress. Cancellation preserves the previous
  result. Showing or hiding the popover during OCR must not cancel recognition.
- Provide login startup and quitting in the icon's right-click menu. Login
  startup opens the app in the background with the popover hidden, using only
  Texo's per-user LaunchAgent and no KeepAlive. Quitting leaves the next-login
  setting intact; disabling startup does not terminate the running app. Report
  startup changes that fail without overwriting unrelated entries.
- Preserve the dependency on this checkout, its virtual environment, models and
  base Python installation. Rebuilding the ad-hoc-signed launcher can require
  screen-recording authorization again. Shortcut rebinding remains future work.
- Publish macOS changes only to the user's fork branch
  `origin/codex/macos-local-ocr`; do not push or merge into `main` or upstream.

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
and copy formats in the native popover, capture before presentation, and showing
progress while OCR is running. Verify login entry creation/removal, background
startup, no KeepAlive, and preservation of unrelated startup entries. Distinguish
a launchctl/background-launch check from an actual logout/login test.

Review the resident UI and login extension against
`2101054bc529d7a9f775d44a4db5558239b8b34b` before committing.
