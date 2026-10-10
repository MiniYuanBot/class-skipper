# class-skipper

[English](README.md)

一个可移植的 agent skill：把课程讲义（PDF/PPTX）和可选讲稿（DOCX/TXT/MD，中英文均可）
整理成中文 Obsidian 学习笔记。支持 **Codex** 和 **Claude Code**，可在 **Windows** 与
**macOS** 上使用。

skill 在当前 agent 会话中分四步完成，可用时把独立任务交给原生子代理：

1. **完整阅读与规划**：读取全部文本单元，并查看带页码的讲义缩略图拼版，补上文字提取
   漏掉的图示和扫描页；规划 4–8 章，标注候选图和每个概念的主讲章节。有讲稿时，
   以讲稿划定本讲范围：上一讲没讲完、本节课补讲的 PPT 归入本讲，本节课没讲到的
   PPT 归入实际讲授它的那一讲，老师指定为拓展的后续内容照样整理并标为“拓展”。
   打开可选开关 `thought_questions` 后，老师布置的思考题会放在对应概念旁，附提示
   和折叠的解答；只有讲稿明确说到考试时才标“考试提示”；`output/questions.md`
   汇总全课程的思考题。
2. **逐章写作**：按固定模板写作，包括本节要点、动机 → 定义 → 机制 → 例题 → 易错点，
   用 Mermaid 画材料中描述的流程，用带标签的提示块区分补充内容，自测题答案默认折叠。
3. **加入可视化**：裁剪讲义原图并查看裁剪结果确认；有联网能力时，附上经过核实的
   外部可视化或交互演示链接。
4. **一次整体校订**：由一位编辑修正覆盖面、准确性、重复和格式；`check` 命令列出
   Markdown 机械问题，在同一次校订中改完。

本地 Python 脚本只负责解析文档、渲染页面、缓存回答和发布文件。不需要 API key、
`.env`、模型 SDK 或外部 OCR；按宿主的正常登录状态和额度运行。

## 安装

需要 Python 3.11+。在本项目目录执行：

```powershell
# Windows（PowerShell）
py -3 tools/install_skill.py
```

```bash
# macOS
python3 tools/install_skill.py
```

默认同时把 `skills/class-skipper` 链接到两个宿主，因此修改本仓库后无需重新安装
（macOS/Linux 使用符号链接，Windows 使用 junction）：

| 宿主 | 默认位置 |
| --- | --- |
| Codex | `$CODEX_HOME/skills/class-skipper`，否则 `~/.agents/skills/class-skipper` |
| Claude Code | `$CLAUDE_CONFIG_DIR/skills/class-skipper`，否则 `~/.claude/skills/class-skipper` |

用 `--host codex` 或 `--host claude` 只装一个，用 `--destination` 指定精确目录
（例如某个项目的 `.claude/skills/class-skipper`）。已存在的文件夹或指向其他位置的链接默认保留不动；
加 `--update` 会先把旧内容改名为 `class-skipper.backup*` 再链接新版本。也可以手动复制整个文件夹。

## 使用

在笔记根目录（Obsidian 仓库）或某门课程目录中启动 agent：

```text
# Codex
使用 $class-skipper 为 computer-organization-and-architecture/input 中的每一讲生成笔记。

# Claude Code
/class-skipper 为 computer-organization-and-architecture/input 中的每一讲生成笔记
```

在 Claude Code 中直接说“帮我把这几讲做成笔记”也会自动加载该 skill。skill 先运行
`scripts/local.py doctor` 检查 Python，只把缺少的解析包（`pypdfium2`、`Pillow`、
`python-docx`、`python-pptx`）安装到 `<课程>/workspace/.venv`。

## 课程清单

把一门课的原始材料放进 `<课程目录>/input/`，例如 `L02/slides.pdf` 和
`L02/transcript.docx`。可选的 `input/course.yaml` 用来明确讲次配对、顺序和运行选项：
复制 [`course.example.yaml`](skills/class-skipper/references/course.example.yaml)
后修改即可。路径相对于清单文件。没有清单时，skill 按文件名配对，配对不清楚时会询问。

```yaml
schema_version: '1'
title: 操作系统
options:
  thought_questions: true                  # 默认 false
  thought_question_terms: [思考题, Think]   # 可选
lectures:
- id: l02
  title: 操作系统的四个基本概念
  slides: [L02/slides.pdf]
  transcripts: [L02/transcript.docx]
```

| 字段 | 含义 |
| --- | --- |
| `title` | 课程名，显示在 `output/index.md` |
| `lectures[].id` | 讲次编号，`l2`、`02`、`L02` 都会统一成 `L02` |
| `lectures[].title` | 本讲主题，笔记标题为 `L02 主题` |
| `lectures[].slides`、`transcripts` | 本讲的全部文件，可以有多个 |
| `options` | 对所有讲次生效的运行选项；`lectures[].options` 可按讲覆盖 |
| `options.thought_questions` | 整理老师布置的思考题，附提示、折叠解答和汇总 |
| `options.thought_question_terms` | 老师对思考题的称呼，用于更精确地识别 |

每讲只需列出本讲自己的 PPT。讲稿补讲了上一讲的 PPT 或提前讲了下一讲的内容时，
skill 会自己读取相邻讲次的 PPT，由讲稿决定每讲笔记的范围。修改选项会让该讲重新
生成，你手工改过的笔记仍然受保护。

## 目录结构

笔记根目录保留 `.obsidian/`；每门课程有独立的 `input/`、`workspace/`、`output/`，
脚本的 `--root` 指向课程目录。

```text
<笔记根目录>/                             Obsidian 仓库根目录
  .obsidian/                             不做修改
  computer-organization-and-architecture/   课程目录（--root）
    input/course.yaml                    可选清单（讲义与讲稿配对、讲次顺序）
    input/L02.pdf, input/L02.docx        讲义和讲稿
    workspace/L02/<run-id>/              材料、计划、任务请求、章节、缩略图/裁剪、
                                         初稿、校订、缓存
    output/index.md                      课程目录
    output/L02/index.md                  章节链接（附一句话摘要）与本讲小结
    output/L02/chapters/01-performance-metrics.md  每章一篇（英文文件名）
    output/L02/assets/l02-isa-formats.png 仅包含被引用的图片
```

文件和文件夹名均为英文，笔记内容为中文。每篇章节笔记包含：YAML 属性
（以中文标题作为 alias，用于链接补全）、顶部和底部的
上一节/下一节及目录导航、本节要点、带公式/例题/原图/Mermaid 的概念小节、折叠的自测题、
关键结论上的脚注，以及合并页码区间后折叠显示的来源列表。发布时保护手工修改：
冲突文件保持原样，新版本作为候选保存在 workspace。旧运行记录保持原路径和
`section-N.md` 文件名。

跨章链接使用指向实际英文文件名的相对 Markdown 路径，显示文字保留中文。
写作者通过稳定的章节 ID 引用，发布时解析；找不到目标或有歧义时报告错误。
正文、摘要、表格和图注中的数学表达统一使用 LaTeX。图片替代文字保持简短、纯文本，
完整图注作为图片下方的独立段落，让公式正常渲染。

详见 [SKILL.md](skills/class-skipper/SKILL.md)、
[流程约定](skills/class-skipper/references/workflow.md)、
[笔记风格](skills/class-skipper/references/note-style.md) 和
[可视化指南](skills/class-skipper/references/visuals.md)。

## 开发

```text
python -m venv .venv
.venv/bin/python -m pip install pypdfium2 python-docx python-pptx Pillow ruff   # Windows：.venv\Scripts\python
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check skills tools tests
.venv/bin/python -m ruff format --check skills tools tests
```

测试使用真实的小型 PDF/DOCX/PPTX/TXT 样例和明确标注的回答替身，不调用模型。
真实运行记录单独见 [CODEX_SKILL_REPORT.md](docs/CODEX_SKILL_REPORT.md)，
架构说明见 [DESIGN.md](docs/DESIGN.md)。
