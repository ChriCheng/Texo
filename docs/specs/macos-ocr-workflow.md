# macOS OCR workflow

## Requested behavior

- Recognize the three supplied formula images and distinguish renderer incompatibility from cropped input. Convert verified equivalent command aliases for Obsidian/MathJax; preserve mathematical and text content.
- Let the user select plain LaTeX, `$LaTeX$`, or `$$LaTeX$$` when copying. Copied text and CLI output have no trailing newline.
- Read image data from the clipboard and recognize it through the same model path as selected files.
- Capture a temporary screen region and recognize it. Cancellation preserves the previous result, and temporary image files are removed.
- Register global Command-L while Texo is running, as explicitly confirmed by the user. It triggers region capture even while another application is in front. Registration failures are visible; closing Texo releases the shortcut.
- Keep the UI responsive and prevent overlapping recognition/capture requests. No training or upload of user images is required.

## Verification

Test the public normalization and copy-format interfaces, CLI bytes, real OCR with file and image inputs, desktop clipboard/display/error recovery, screenshot cancellation and cleanup, and macOS hotkey registration/dispatch. Separately report native region selection or hardware keyboard checks that require user interaction.

Review against the deployment starting point `5abd60b66708e59a5b53834b04bde10285de15cd` before committing.
