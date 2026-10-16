<p align="center" style="margin-bottom: 0">
  <img src="./assets/svg/logo-text.svg#gh-light-mode-only" alt="Texo Logo" width="300"/>
  <img src="./assets/svg/logo-text-dark.svg#gh-dark-mode-only" alt="Texo Logo" width="300"/>
</p>
<p align="center" style="font-size: 0.9em">
Texo is pronounced as /ˈtɛːkoʊ/
</p>
<p align="center">
  A minimalist free and open-source SOTA LaTeX OCR model which contains only 20M parameters.
</p>

<div align="center">
  
  [Try it online](https://texocr.netlify.app)
  
</div>
<div align="center">
  
  Technical report: [arXiv](https://arxiv.org/abs/2602.17189), [HAL](https://hal.science/hal-05510395)

</div>

## Features
- Free and open-source.
- Fast and lightweight inference.
- Trainable on consumer's-level GPU.
- Well organized code as a tutorial.
- [Running in browser!](https://github.com/alephpi/Texo-web)

## Prelude
Despite a growing number of STEM and AI learners with their note-taking needs today, a free, fast, more accessible yet precise LaTeX OCR tool is still absent. Lying exactly in the comfort zone of machine learning due to the closed vocabulary and less generalization requirements, such classical pattern recognition task can be considered as solved thanks to recent deep learning progress(TrOCR, GOT-2.0, UniMERNet, PPFormulaNet). So here comes the Texo, which tackles this problem in the scope of a personal project.

It is also a comprehensive practice to combine the knowledge and experiences I learned so far from school and online, as well as a tentative contribution to my beloved open source community.

## Performance

Texo is a distilled version of PPFormulaNet-S and finetuned on UniMERNet-1M, hence it should preserve the most part of the performance compared to PPFormulaNet-S. Here is the evaluation results on the UniMERNet-Test dataset.

|               Model               |      Params      | Metric        | SPE    | CPE    | SCE    | HWE    |
| :-------------------------------: | :--------------: | ------------- | ------ | ------ | ------ | ------ |
|  UniMERNet-T<sup>&dagger;</sup>   |       107M       | BLEU          | 0.909  | 0.902  | 0.566  | 0.883  |
|                                   |                  | Edit distance | 0.066  | 0.075  | 0.239  | 0.078  |
| PPFormulaNet-S<sup>&dagger;</sup> |       57M        | BLEU          | 0.8694 | 0.8071 | -      | -      |
|                                   |                  | Edit distance | -      | -      | -      | -      |
|     Texo-distill<sup>*</sup>      |       20M        | BLEU          | 0.9014 | 0.8909 | 0.7034 | 0.8606 |
|                                   |                  | Edit distance | 0.0780 | 0.1042 | 0.1941 | 0.0995 |
|     Texo-transfer<sup>*</sup>     | 20M<sup>**</sup> | BLEU          | 0.8597 | 0.8334 | 0.5549 | 0.7973 |
|                                   |                  | Edit distance | 0.0980 | 0.1306 | 0.2187 | 0.0999 |
|     Texo-transfer-onnx            |     as above     | BLEU          | 0.8395 | 0.8136 | 0.5153 | 0.7787 |
|                                   |                  | Edit distance | 0.0980 | 0.1288 | 0.2050 | 0.0976 |

We only list the lightweight version for the SOTA models, as we can see in terms of sequential metrics like BLEU or Edit distance, our model has comparable performance while reducing a lot of parameters. 

> `-` means not reported in the paper.
> 
> &dagger;: Copy from the paper
> 
> *: Texo-distill uses the same tokenizer as UniMERNet and PPFormulaNet, hence the sequential metrics are strictly comparable. While Texo-transfer uses a customized tokenizer hence the metrics are not comparable (we have a shorter sequence length, see more in [notes](./TechnoSelection/notes.md)).
> 
> **: Slightly less than Texo-distill as the tokenizer's vocab is smaller.

 <img width="2035" height="480" alt="image" src="https://github.com/user-attachments/assets/273e115a-4bbf-4a0f-a3d5-54746c417fa7" />


## Configure environment

### macOS local OCR (no training)

This fork includes a native menu-bar application for selecting an image,
recognizing a clipboard image, or capturing a temporary screen region with
global **Command-L**. Its white popover shows the image on the left and an
editable recognition result on the right.
The default **中文与公式** mode recognizes single-column Chinese/English prose
and formulas together, producing Markdown suitable for Obsidian. Formula crops
use the existing Texo model; prose uses macOS Vision and regions are detected
with [Pix2Text MFD 1.5](https://huggingface.co/breezedeus/pix2text-mfd-1.5).
Images stay on your Mac; no training or OCR service is required.

Use Python 3.11 or 3.12 with Tk support. Check your interpreter first:
`python3 -c 'import tkinter; print(tkinter.TkVersion)'`.
If it reports a missing `_tkinter`, use a Python installation that includes Tk
(for example, a Conda environment with `python=3.11 tk`).
Chinese recognition also requires macOS 13+ and Apple Command Line Tools
(`xcode-select --install` if they are missing). A small Vision helper compiles
automatically on first use and is cached under `.local/bin`; a cold Swift module
cache can make the first recognition take several minutes.

```sh
git clone --branch main https://github.com/ChriCheng/Texo.git
cd Texo
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python scripts/python/hf_hub.py pull --mixed
./launch_macos.command
```

After setup, use the application below or double-click `launch_macos.command`.

For a local **Texo.app** that opens from Spotlight or Finder without a terminal:

```sh
.venv/bin/python scripts/python/build_macos_app.py --output /Applications/Texo.app
open /Applications/Texo.app
```

If `/Applications` is not writable, use `--output ~/Applications/Texo.app`.
After installation, press **Command-Space**, search **Texo** and press Return.
Opening it again shows the existing popover. Texo stays in the menu bar without
a Dock icon. Left-click or right-click its menu-bar icon to open the menu. Choose
**显示／收起结果** or press **Command-Shift-;** to show or hide the result.
**Esc** in the popover or clicking outside it only hides the popover;
recognition and the global shortcuts remain available. Open the icon's menu and
choose **退出 Texo**, or use **Command-Q** while Texo is active, to quit and release
both shortcuts. To change them, choose **快捷键设置** in the icon's menu, click a recording
button and press the new combination, then click **应用**. The two combinations
must differ and include Command, Control or Option. Common editing shortcuts
are reserved. Texo pauses its global shortcuts while settings are open;
**取消** restores the saved combinations. **恢复默认** changes the draft, and
**应用** makes it effective. Occupied combinations show an error without saving.
The menu and screenshot button update immediately, and settings survive restart.

The normal menu-bar icon uses the original logo's four scan corners and
outlined formula, adapting to light or dark menu bars. During recognition it
changes to a pie-style progress indicator after image acquisition. The sector
smoothly fills as processing stages or formula regions finish, then holds
until the next stage completes. It shows completed work, not estimated time.
Completion, failure and cancellation restore the normal icon. Single-formula
results display the selected `LaTeX`, `$LaTeX$` or `$$LaTeX$$` format directly;
changing the format keeps edits and updates the displayed delimiters. Ordinary copying
uses the same text, without adding another pair of delimiters.

Open the icon's menu and enable **登录时自动启动** to launch Texo in the background
after logging into this Mac. The popover stays hidden until requested. This
creates only Texo's per-user entry at
`~/Library/LaunchAgents/com.chricheng.texo.login.plist`; it has no `KeepAlive`, so
quitting does not immediately restart Texo. Quitting preserves the next-login
setting, and turning the setting off leaves the currently running app open.

This is a small application for the current Mac: it embeds the existing Python
runtime in the app process and reuses this checkout's `.venv`, model files and
base Python installation. Keep those locations in place; rebuild the app if
the project moves. It is not a standalone package for another computer.
Startup diagnostics are appended to `.local/texo-app.log` in the project.

The application has its own macOS screen-recording identity. On the first
capture, allow **Texo** in System Settings → Privacy & Security → Screen
Recording, then fully quit and reopen it. The previous terminal's authorization
does not authorize the application. The local app is ad-hoc signed; rebuilding
the native launcher can change its code identity and require authorizing it
again. The switch can remain on even when the current signature or running
process no longer has effective access. If capture is blocked, fully quit Texo,
turn its Screen Recording switch off and back on, then reopen it. If this still
fails, quit Texo and run `tccutil reset ScreenCapture com.chricheng.texo`, then
reopen and authorize Texo again; this resets only Texo's permission record.
Python backend updates only require restarting Texo and preserve the existing
native app signature; rebuild when native app sources or the runtime paths
change. Models and user images remain local.

Choose an input in either the app or terminal-launched window:

- **选择图片** opens a saved text or formula image.
- **识别剪贴板** recognizes image data on the clipboard. On macOS,
  **Command-Control-Shift-4** captures a selected region to the clipboard.
- **截图识别 ⌘L** captures a region directly. Global **Command-L** triggers the
  same capture while another app is in front. Texo must remain running; this
  takes precedence over other apps' Command-L action. The popover hides before
  region selection and stays hidden during recognition by default. When
  recognition succeeds, Texo displays the captured image and result and copies
  the result automatically. Use **Command-Shift-;** or the menu to inspect progress
  while recognition is running. Quit Texo to release the shortcut.
  A shortcut registration conflict is shown in the status line.

Press **Esc** to cancel a capture and keep the previous result. Temporary
screenshots are deleted after loading. If macOS blocks screen capture, allow
screen recording for Texo.app, or for the terminal if launching from a terminal,
in System Settings, then relaunch as prompted. Texo checks this
permission before capture: a successful screenshot command alone can still
return only desktop wallpaper when access to application content is denied.

Choose the recognition mode in the menu before selecting an image or capturing.
Texo.app remembers the mode and pure-formula copy format after restarting:

- **中文与公式** keeps prose outside math, inserts `$...$` around inline formulas
  and `$$...$$` around display formulas, and copies the complete Markdown. If
  the recognized result contains only one formula and no prose, Texo.app uses
  the pure-formula copy format instead, including its default `$$...$$` wrapper.
  The result panel's format selector is disabled for results that include mixed prose.
- **公式** recognizes one formula. Select **LaTeX**, **$LaTeX$**, or **$$LaTeX$$**
  in the format menu to copy plain source, inline math, or display math. The
  default pure-formula format in Texo.app is **$$LaTeX$$**.

In Texo.app, file, clipboard and screenshot recognition stay hidden by default
while OCR runs; the icon shows activity. Successful recognition displays the
result and copies its format automatically. Use **Command-Shift-;** or the menu
to inspect progress without waiting. Click **复制结果** again after checking or
editing the result. Neither mode adds a trailing newline. Failure or cancellation
leaves the existing clipboard intact.
Changing the mode affects the next recognition and preserves the current
result's copy behavior. The terminal-launched window uses its **复制结果** button;
the CLI also omits the trailing newline.

The native result editor supports **Command-A**, **Command-C/X/V**, **Command-Z**
and **Command-Shift-Z** while it has keyboard focus. Manual edits and changes
to copy delimiters can be undone. Each new recognition starts a new undo history.

All settings appear directly in the icon's menu, with separators between groups.
Under **默认复制方式**, check **普通复制** (the default) or **PPT 专用复制**.
The two choices are mutually exclusive and survive restart. Recognition's
automatic copy and the menu's **复制结果** action follow this choice.
The result panel always provides **复制公式** for LaTeX/Markdown text and
**复制到 PPT** for rich Office content. Both use the current edited result,
independently of the default. Command-C in the editor copies selected text.
Ordinary copy produces the selected LaTeX/Markdown text; PPT copy preserves
Chinese prose and converts math into rich content with editable Office equations.
PPT copy supplies HTML with MathML without a raw LaTeX text fallback; use
**复制公式** for Obsidian or other text editors. The converter runs locally using Pandoc
(`brew install pandoc` if missing); a conversion error leaves the clipboard
unchanged. Supported formula commands depend on Pandoc and PowerPoint's MathML
importer. This is not a full LaTeX document compiler, and it does not transfer
document themes or slide layouts.
The empty-set alias `\empty` is normalized to `\emptyset`. Unsupported commands
are named in the error message; conversion failure preserves the clipboard.

`launch_macos.command` still opens the terminal-launched desktop window; closing
that window quits that instance. Menu-bar residency and login startup belong to
Texo.app. This fork's personal macOS version is maintained on
**ChriCheng/Texo:main**. Develop changes on feature branches, such as
`codex/macos-local-ocr`, and merge tested changes into this fork's `main`.
Upstream updates from `alephpi/Texo` are reviewed and merged only when the user
chooses; do not configure automatic upstream synchronization or push to upstream.

The extra detector is approximately 80 MB and is stored as `model/mfd.onnx`.
If already installed by Pix2Text, its existing
`~/.pix2text/1.1/mfd-1.5-onnx/pix2text-mfd-1.5.onnx` cache is reused. Weights,
Swift build products and user screenshots are not included in this repository.

Texo's verified KaTeX aliases `\larr` and `\infin` are converted to the equivalent
`\leftarrow` and `\infty` commands for Obsidian/MathJax. Cropped-away formula
content is not reconstructed. You can also recognize a file directly:

```sh
.venv/bin/python main.py path/to/formula.png
.venv/bin/python main.py --mode mixed path/to/chinese-and-math.png
.venv/bin/python -m unittest discover -s tests -v
# Optional: include the desktop callback and clipboard test in a GUI session.
# Quit any running Texo instance first to release its global shortcuts.
TEXO_TEST_GUI=1 .venv/bin/python -m unittest discover -s tests -v
```

The OCR integration tests use locally rendered formula, Chinese and mixed
fixtures under `tests/fixtures`. Native Chinese and desktop tests require
`TEXO_TEST_GUI=1` in a normal macOS session. Review output before using it:
complex formulas, unusual fonts and low-resolution images can be misrecognized.
Mixed reading order currently supports single-column crops; multi-column pages,
tables and handwriting have not been validated.

### Full training environment

```sh
git clone https://github.com/alephpi/Texo
uv sync
```
> For those who don't use uv, it worths to try it. For those who insist not to use, I guess you know how to adapt.

## Download model
```sh
# model only
python scripts/python/hf_hub.py pull
```
```sh
# for those who want to train from useful checkpoints
python scripts/python/hf_hub.py pull --with_useful_ckpts
```

## Inference
Check [`demo.ipynb`](./demo.ipynb)

## Training

### Requirements
- Mine: 50G CPU memory, A40/L40S 46G.
- Recommend: 50G CPU memory, 40G GPU memory.
- Minimal: 20G CPU memory(with streaming dataloading) and 16G GPU memory(with accumulative gradient).

### Download dataset (UniMER-1M)
Following https://huggingface.co/datasets/wanderkid/UniMER_Dataset as what I've done

If you are lazy, use the one that I arranged and normalized.
- https://huggingface.co/datasets/alephpi/UniMER-Train
- https://huggingface.co/datasets/alephpi/UniMER-Test

If you are interested in all the preprocessings, check [here](./data/tokenizer) and [here](./scripts/python/normalize.py), where I collected and sorted all the useful KaTeX commands.

### Launch
We use `hydra` to manage training configurations and experiments.

```sh
# train
python src/train.py
```
```sh
# resume from a checkpoint
python src/train.py training.resume_from_ckpt="<ckpt_path>"
```
```sh
# debug
python src/train.py --config-dir="./config" --config-name="train_debug.yaml"
```
```sh
# train on a slurm cluster
python src/train.py --multirun --config-dir="./config" --config-name="train_slurm.yaml"
```
See other training configurations in [config](./config/) directory.

### Log
The training results are stored in [outputs](./outputs) directiory. To visualize it, run

```sh
tensorboard --logdir outputs
```

### Figures
Some beautiful loss curves to give you an impression of the loss scale and the convergence process.

#### Training loss
<img src="./assets/train_loss.png">

#### Validation loss
<img src="./assets/val_loss.png">

#### BLEU
<img src="./assets/BLEU.png">

#### Edit distance
<img src="./assets/edit_distance.png">

#### Learning rate
<img src="./assets/learning_rate.png">

## Reproduce the whole work

If you want to start from scratch, check my [notes](./TechnoSelection/notes.md)

## Acknowledgements

- [transformers](https://github.com/huggingface/transformers): framework, model decoder, tokenizer
- [UniMERNet](https://github.com/opendatalab/UniMERNet): dataset, image processor
- [Im2Markup](https://github.com/harvardnlp/im2markup): latex preprocessing
- [KaTeX](https://github.com/KaTeX/KaTeX): latex vocabulary for training tokenizer and latex parser for preprocessing
- [my-unimernet](https://github.com/ParaN3xus/my-unimernet/blob/main/unimernet/components/processor/image_processor.py): image processor (plus a nice codebase to demystify UniMERNet)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR/blob/main/ppocr/modeling/backbones/rec_pphgnetv2.py): model architecture, pretraining weights
- [PaddleOCR2Pytorch](https://github.com/frotms/PaddleOCR2Pytorch) and [D-FINE](https://github.com/Peterande/D-FINE): model encoder implementation
- [Im2Markup](https://github.com/harvardnlp/im2markup), [LaTeX-OCR](https://github.com/lukas-blecher/LaTeX-OCR) and [TrOCR](https://github.com/microsoft/unilm/tree/master/trocr): pioneers
- [MixTeX](https://github.com/RQLuo/MixTeX-Latex-OCR) and [TexTeller](https://github.com/OleehyO/TexTeller): motivation
- Telecom Paris for providing the GPU cluster.

>[!Note]
> Feel honored been collected in [@ruanyf's weekly](https://www.ruanyifeng.com/blog/2025/11/weekly-issue-372.html), if you are a user from there, and have an issue on visit the website, please leave a message in [Texo-web](https://github.com/alephpi/Texo-web) repo. Due to my limited front-end skills, please contribute to help me in any form.
> 
> 很荣幸被 [《阮一峰的科技周刊》](https://www.ruanyifeng.com/blog/2025/11/weekly-issue-372.html) 收录，如果你从那里过来，并且在访问 demo 网站时出现 bug，请移步至 [Texo-web](https://github.com/alephpi/Texo-web) 仓库报告。由于我前端水平有限，欢迎各位不吝赐教。

感谢<a href="https://linux.do" alt="LINUX DO"><img src="https://shorturl.at/ggSqS" /></a>的宣传

## License
[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

Copyright (C) 2025-present Sicheng Mao <maosicheng98@gmail.com>

## Authorization
A limited, non-transferable LGPL-2.1 license is specially granted to Charlie for sole use within the macOS app [Texo OCR](https://github.com/zclk9000/texoocr) only.
All other usages are subject to AGPL-3.0 by default.

## Star History

[![Star History Chart](https://star-history.dera.page/svg?repos=alephpi/Texo&type=date&legend=top-left)](https://star-history.dera.page/#alephpi/Texo&type=date&legend=top-left)
