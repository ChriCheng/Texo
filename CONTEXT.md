# Texo OCR

Texo converts formula images into editable LaTeX, or single-column Chinese text
and formula screenshots into Markdown on macOS.

## Language

**Recognition result**: The formula source decoded from an image, with equivalent command aliases made compatible with the user's math renderer. It does not reconstruct content outside the image.

**Copy format**: The recognition result copied as plain LaTeX, inline math enclosed in single dollar signs, or display math enclosed in double dollar signs. No format includes a trailing newline.

**Mixed result**: Chinese/English prose in reading order, with detected inline
formulas enclosed in single dollar signs and display formulas in double dollar
signs. Copy preserves the complete Markdown without wrapping the prose in math.

**Recognition mode**: Formula mode sends one formula to Texo. Mixed mode detects
formula regions with Pix2Text MFD, recognizes those crops with Texo, and reads
the remaining text with macOS Vision. Images remain local.

**Clipboard image**: Image data currently on the macOS clipboard, rather than a path copied as text.

**Temporary capture**: A user-selected screen region used for recognition without leaving a screenshot on the desktop.

**Global shortcut**: A key combination that triggers Texo while another application is in front, for as long as Texo is running.
