# macOS OCR workflow

## Requested behavior

- Recognize the three supplied formula images and distinguish renderer incompatibility from cropped input. Convert verified equivalent command aliases for Obsidian/MathJax; preserve mathematical and text content.
- Let the user select plain LaTeX, `$LaTeX$`, or `$$LaTeX$$` when copying. Copied text and CLI output have no trailing newline.
- Read image data from the clipboard and recognize it through the same model path as selected files.
- Capture a temporary screen region and recognize it. Cancellation preserves the previous result, and temporary image files are removed.
- Register global Command-L while Texo is running, as explicitly confirmed by the user. It triggers region capture even while another application is in front. Registration failures are visible; closing Texo releases the shortcut.
- Keep the UI responsive and prevent overlapping recognition/capture requests. No training or upload of user images is required.
- Extend recognition to Chinese text mixed with formulas, as explicitly selected
  by the user. Preserve text/formula reading order in a single-column screenshot.
  Use Markdown with inline and display math delimiters for mixed output; do not
  wrap the entire Chinese result in math. Keep pure formula mode and its three
  copy formats available. Both modes work for files, clipboard images and captures.

## Verification

Test the public normalization and copy-format interfaces, CLI bytes, real OCR with file and image inputs, desktop clipboard/display/error recovery, screenshot cancellation and cleanup, and macOS hotkey registration/dispatch. Separately report native region selection or hardware keyboard checks that require user interaction.

Verify literal Chinese/English/numeric text and a self-rendered screenshot with
Chinese on both sides of an inline formula plus a display formula. Exercise mode
switching and Markdown copying without a trailing newline. Report model errors
and missing native tools/model files instead of silently dropping content.

Review the mixed recognition extension against `1c350341d14823af7230307d139276961433656a` before committing.
