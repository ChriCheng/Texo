# Texo OCR

Texo converts formula images into editable LaTeX, or single-column Chinese text
and formula screenshots into Markdown on macOS.

## Language

**Recognition result**: The formula source decoded from an image, with equivalent command aliases made compatible with the user's math renderer. It does not reconstruct content outside the image.

**Copy format**: The recognition result copied as plain LaTeX, inline math enclosed in single dollar signs, or display math enclosed in double dollar signs. The native app defaults to display math and remembers the selection. No format includes a trailing newline.

**Copy mode**: A saved, mutually exclusive default for automatic copy and the
menu's copy action. The result panel has separate text and PPT copy buttons
that always use their named format and the current edited result.

**PPT copy**: Preserves prose and converts formula source in the result into
rich content for PowerPoint's editable equations. Ordinary copy keeps the
selected LaTeX or Markdown text. PPT copy supplies formula-rich HTML without a
plain LaTeX fallback; the text button supplies the source for math renderers.

**Result editing**: Standard text selection, copy, cut, paste, undo and redo
within the focused result editor, including undo of manual edits and format
changes. A newly recognized image starts a new editing history.

**Mixed result**: Chinese/English prose in reading order, with detected inline
formulas enclosed in single dollar signs and display formulas in double dollar
signs. Copy preserves the complete Markdown without wrapping the prose in math.
When mixed recognition returns only one formula without prose, the native app
treats it as a formula result and uses the selected pure-formula copy format.

**Recognition mode**: Formula mode sends one formula to Texo. Mixed mode detects
formula regions with Pix2Text MFD, recognizes those crops with Texo, and reads
the remaining text with macOS Vision. Images remain local.

**Clipboard image**: Image data currently on the macOS clipboard, rather than a path copied as text.

**Temporary capture**: A user-selected screen region used for recognition without leaving a screenshot on the desktop.

**Global shortcut**: A key combination that triggers Texo while another application is in front, for as long as Texo is running.

**Shortcut settings**: Separate saved combinations for screenshot recognition
and showing or hiding the result, defaulting to Command-L and
Command-Shift-semicolon. Recording creates a draft; Apply saves available
combinations, while Cancel preserves the previous ones.

**Resident popover**: The native white menu-bar interface with image preview on
the left and editable result on the right. Either mouse button opens the icon's
menu; all settings appear at its first level in separated groups. Its show/hide
item or global Command-Shift-semicolon toggles the popover.
Escape or an outside click hides it without quitting. Global Command-L starts
region selection. File, clipboard and screenshot recognition keep the popover
hidden during OCR by default; users can still request progress. Success shows
and automatically copies the completed result. Single-formula results display
the selected copy delimiters; changing the format rewraps the current edits.
Failure or cancellation preserves the clipboard. The shortcut settings can
replace both default combinations.

**Recognition activity**: A pie-style menu-bar indicator replaces the normal
four-corner formula icon only after image acquisition, while recognition runs.
Its sector smoothly fills to completed processing stages (or formula regions
in mixed mode), holds while the current stage runs, and never estimates time.
Completion, failure and cancellation restore the normal icon.

**Login startup**: Opens Texo.app in the background after login, with the popover
hidden. Quitting does not restart the app immediately and leaves the next-login
setting enabled; disabling startup does not quit the current app. The menu-bar
icon's menu controls startup and quitting.

**Local application**: A native Texo.app that runs the existing Python environment
in the same process. LaunchServices opens one instance and macOS attributes its
window and screenshot permissions to Texo. It requires the current checkout,
virtual environment, models and base Python paths to stay available.
The native app stays in the menu bar without a Dock icon; quitting
releases its shortcuts. The terminal-launched Tk window remains a fallback.

**Maintenance branch**: `ChriCheng/Texo:main` is the stable personal macOS
version, with feature branches holding changes under development. The upstream
`alephpi/Texo` is an optional update source whose changes require the user's
manual decision to merge.
