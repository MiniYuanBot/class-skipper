# class-skipper

[English](README.md)

## Codex skill（Windows 和 macOS）

可独立安装的 [class-skipper skill](skills/class-skipper/SKILL.md) 使用当前
Codex 会话完成四步：完整阅读与规划、逐章写作、可选的选择性读图、一次整体
校订。独立章节、候选图和最后一次校订优先交给可用的 Codex 子代理；本地
Python 助手负责解析、保存完整回答缓存和保护手工修改。这个模式不需要提供商
API key，不读取 `.env`，不调用模型 HTTP 客户端。
仍需正常登录 Codex，并消耗其使用额度。没有子代理工具时按同一流程顺序完成；
读图需要当前宿主支持查看图片。

在项目目录使用 Python 3.11+ 安装：

```powershell
# Windows PowerShell
python tools/install_skill.py
```

```bash
# macOS
python3 tools/install_skill.py
```

如果设置了 `CODEX_HOME`，安装到 `CODEX_HOME/skills/class-skipper`；否则安装到
`~/.agents/skills/class-skipper`。其他宿主的 skill 目录可用 `--destination` 指定
完整目标文件夹。已有安装内容不一致时会保留原文件，不直接覆盖。也可将整个
`skills/class-skipper` 文件夹复制到 skill 目录，复制后无需保留本项目源码。
本地发现规则见 [官方 skill 文档](https://learn.chatgpt.com/docs/build-skills)。

在 Codex 中调用：

```text
使用 $class-skipper 完整读取 input/course.yaml 的每份材料，用子代理生成中文笔记，
输出到当前工作区，按需检查有用的机制图，最后只做一次整体校订。
```

提供实际材料路径或课程清单，也可指定已授权的 Obsidian 仓库。缺少本地解析
依赖时按需安装：TXT/Markdown 只用 Python 标准库，PDF/DOCX/PPTX 分别需要
`pypdfium2`、`python-docx`、`python-pptx`。离线命令与中间文件约定见
[workflow.md](skills/class-skipper/references/workflow.md)。

## Skill 的输入、中间文件和输出结构

使用者把材料放入 `input/`，可按课程、讲次分文件夹。课程清单用于明确讲义与
转录的对应关系和讲次顺序。skill 默认以当前项目目录为根目录，也支持显式
指定其他材料路径，无需移动原文件。运行数据和模型任务 JSON 使用
`schema_version: 1`、UTF-8 编码，统一留在 `workspace/`，保留已有运行记录和完整回答缓存。

```text
input/os/l02/                 用户提供的讲义和转录
workspace/os/l02/<run-id>/    materials.json、run.json、status.json、plan.json
  requests/                  各项任务的完整请求
  chapters/                  每个板块的完整回答 JSON
  visuals/pages/、crops/      原页渲染和候选裁图
  visuals/readings.json      实际读图结果
  draft/notes.md             交给唯一一次校订的完整初稿
  revision/review.json       校订结果
  final/document.json        校订后的结构化笔记
  cache/                    完整回答及刷新历史
output/
  index.md                   全部课程目录
  os/index.md                课程内的讲次目录
  os/l02/index.md            讲次内的板块目录、导读和小结
  os/l02/chapters/section-1.md
  os/l02/chapters/section-2.md
  os/l02/assets/diagram.png
```

每个主要板块是一篇独立的 Obsidian 笔记，统一包含 YAML 属性、标题、返回目录
链接、概念讲解、公式、例子、问答与来源定位。`output/` 只包含最终 Markdown、
目录和被引用的图片，可以直接作为 Obsidian 仓库打开，从 `index.md` 开始阅读。
导出到现有仓库时，会在指定课程文件夹内保留根目录和课程 ID 子目录，形成
完整的单课程笔记库，让相对导航链接保持有效。手工修改过的目录、章节和图片
受到保护，替换候选留在 `workspace/`。

## 开发与验证

测试使用 Python 标准库 unittest。在项目目录安装本地解析及检查依赖后运行；
macOS 将 `python` 换成 `python3`：

```text
python -m pip install pypdfium2 python-docx python-pptx Pillow ruff PyYAML
python -m unittest discover -s tests -v
python -m ruff check skills tools tests
python -m ruff format --check skills tools tests
```

本地文件测试覆盖解析、缓存、发布和导出保护，不调用模型。真实 Codex 试跑
证据及平台验证范围见 [CODEX_SKILL_REPORT.md](docs/CODEX_SKILL_REPORT.md)，
当前架构见 [DESIGN.md](docs/DESIGN.md)。
