# class-skipper

[English](README.md)

把课程讲义和课堂转录整理为可学习的笔记，并按课程名输出到 Obsidian。
核心流程保持四步：

**完整读取材料 → 理解并规划章节 → 逐章写作 → 一次整体审核校订。**

可选的 Kimi 视觉模块负责寻找流程图、机制图，裁切后复核，再放到对应解释旁。
不使用质量评分作为发布门槛；缺失章节和仍需核验的问题会明确显示。

## 快速开始

以下命令均在本项目目录执行。需要 Python 3.11+，目前支持 macOS/Linux。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
cp .env.example .env
```

在 `.env` 中填写自己的密钥与模型名。实际测试使用的配置为：

```dotenv
DEEPSEEK_API_KEY=your_key
CLASS_SKIPPER_TEXT_MODEL=deepseek-flash
CLASS_SKIPPER_REVIEW_MODEL=deepseek-flash
MOONSHOT_API_KEY=your_key
CLASS_SKIPPER_VISION_MODEL=kimi-k3
CLASS_SKIPPER_KIMI_BASE_URL=https://api.moonshot.cn/v1
```

创建 `configs/local.yaml`：

```yaml
allow_remote_llm: true
vision: true
output: output
workspace: workspace
obsidian_vault: /你的/Obsidian仓库/绝对路径
```

`allow_remote_llm` 允许将课程文本发送给已配置的服务；开启视觉识别后，还会把 PDF 页面图片和裁图发送给 Kimi。
只需要文字笔记时，设置 `vision: false`。不需要自动导出时，设置 `obsidian_vault: ""`。
密钥、本地配置、私人材料、output 和 workspace 均已加入 Git 忽略规则。
项目启动脚本会优先使用本目录的 `.venv`。

```bash
./class-skipper doctor
```

该命令检查文本模型配置与运行依赖，不调用 API。
当前工作区里的私人 `.env`、本地配置和 L02–L04 测试材料属于本机环境，不是每次安装都自带的文件。

## 单指令生成一讲

```bash
./class-skipper generate os l02 \
  --slides input/L02.pdf --transcript input/L02.docx \
  --title "操作系统 · 四个基本概念" --course-name "operating-system"
```

- `os` 是稳定的课程 ID，`l02` 是讲次 ID，使用英文字母、数字、下划线或连字符。
- `--title` 是这一讲的标题。
- `--course-name` 是 Obsidian 中的课程目录名，可以包含中文或空格。
- 未指定课程目录名时，导出会采用课程索引标题；首次单讲生成的索引标题默认为课程 ID。

多个文件可以重复传入 `--slides`、`--transcript`，课堂转录可以省略。
支持 PDF、PPTX、DOCX、TXT 和 Markdown。PPTX 如需提取机制图，请同时提供导出的 PDF；
纯扫描材料需要先提供 OCR 文本或课堂转录，才能进行完整材料规划。

## 单指令生成课程笔记库

把课程清单放在材料旁，例如 `input/course.yaml`：

```yaml
title: operating-system
lectures:
  - id: l02
    title: Four fundamental concepts of OS
    slides: [L02.pdf]
    transcripts: [L02.docx]
  - id: l03
    title: process, syscall and fork
    slides: [L03.pdf]
    transcripts: [L03.docx]
```

```bash
./class-skipper batch os --manifest input/course.yaml --vision
```

材料路径相对于清单所在目录解析。按清单顺序处理各讲，一讲失败不会阻止后续讲次运行。
清单中的 `title` 用作课程索引标题，默认也用作 Obsidian 课程目录名。
配置了 `obsidian_vault` 后，成功生成会自动导出，无需再执行第二条命令。

## 接入 Obsidian

已有笔记可以直接导出，不重新生成，也不调用模型：

```bash
./class-skipper export os --course-name "operating-system"
```

临时指定其他仓库：

```bash
./class-skipper export os --vault /仓库的绝对路径 --course-name "operating-system"
```

请指向实际的仓库根目录，通常就是包含 `.obsidian` 的目录。
当前本机已配置的输出位置是：

```text
/Users/miniyuan/__miniyuan__/class-notes/miniyuan/operating-system/
├── index.md
├── l02.md
├── l03.md
├── l04.md
└── assets/
    ├── l02/
    ├── l03/
    └── l04/
```

在已有 Obsidian 仓库中打开 `operating-system/index.md` 即可阅读。
导出时会调整课程索引和图片的相对链接，只复制真正被引用的图片。
无需安装 Obsidian 插件，也不会修改 `.obsidian` 配置或无关的个人笔记。

这是从 class-skipper 到 Obsidian 的单向发布，不是双向同步。
重复导出时，相同文件不会重写。如果已经在 Obsidian 中修改过导出的笔记或图片，
程序会保留修改，返回退出码 `5`，并把完整新版本留在
`workspace/obsidian/.../candidates/` 供对照；该次导出不会写入有冲突的课程文件。
之前由程序生成、未被修改且不再引用的图片，会在同步时移除。
自动导出仅在生成成功后进行，不完整的笔记暂留本地。

## 目录与常用选项

```text
input/                 课程材料与清单
output/<课程ID>/       最终笔记、课程索引和引用图片
workspace/runs/        完整材料、提纲、草稿、校订记录和视觉检查
workspace/cache/       可复用的完整模型回答
workspace/published/   本地生成文件的校验记录
workspace/backups/     本地历史发布版本
workspace/obsidian/    Obsidian 导出记录与冲突候选版本
workspace/reports/     批量生成报告
```

| 选项 | 用途 |
| --- | --- |
| `--vision` / `--no-vision` | 开启机制图识别 / 使用更快的纯文本流程 |
| `--resume` | 显式启用默认的缓存续跑行为 |
| `--refresh` | 不复用已有回答，重新调用模型 |
| `--no-review` | 跳过最后的整体校订 |
| `--vault`、`--course-name` | 临时指定 Obsidian 仓库和课程目录名 |
| `--config`、`--env-file`、`--output`、`--workspace` | 全局参数，放在子命令之前 |

其他配置见 `configs/default.yaml` 和 `src/class_skipper/config.py`。
默认同时执行三个章节或网络请求，最多保留三张通过复核的图。
规划阶段读取完整提取文本；材料过大时会明确报错，不会静默丢弃后半部分。
写作提示遵循 `references/original` 中的规则，包括概念层级、对比表、公式解释和有用的问答。
首次视觉识别会增加联网调用；缓存复跑通常快得多，但首次耗时仍受网络和模型响应影响。

遇到网络故障，直接重跑同一条命令即可复用成功结果并补齐缺失部分。
本地 output 中的人工修改同样受到保护：新版本会保存在对应运行的 `candidate` 目录，
不会覆盖已编辑笔记。校订服务不可用时会保留初稿并附上提示，不丢弃已完成章节。

退出码：`0` 完成；`2` 配置、输入或导出错误；`3` 章节不完整或批量任务失败；
`5` 检测到人工修改并已保留。批量任务中有讲次失败时总体返回 `3`，具体原因见各讲结果。

## 开发与验证

```bash
.venv/bin/python -m pip install pytest ruff
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools
.venv/bin/python -m ruff format --check src tests
```

测试中的模拟模型有明确标注，不与真实调用混淆。
L02–L04 的实际 API 与裁图验证见 [REBUILD_REPORT.md](docs/REBUILD_REPORT.md)，
设计与参考项目见 [DESIGN.md](docs/DESIGN.md)。自动检查不等于学术内容完全准确，
笔记仍应结合课程材料判断。原项目保存在同级目录 `class-skipper-old`。
