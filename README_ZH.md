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
使用 $class-skipper 完整读取 <课程目录>/input/course.yaml 的每份材料，用子代理生成中文笔记，
输出到当前工作区，按需检查有用的机制图，最后只做一次整体校订。
```

提供实际材料路径或课程清单，也可指定已授权的 Obsidian 仓库。缺少本地解析
依赖时按需安装：TXT/Markdown 只用 Python 标准库，PDF/DOCX/PPTX 分别需要
`pypdfium2`、`python-docx`、`python-pptx`。离线命令与中间文件约定见
[workflow.md](skills/class-skipper/references/workflow.md)。

笔记优先给出知识结论及必要条件，用简单语言表达，并保留有用的推导和例子。
写作者与编辑共用同一写作提示：减少围绕证据和误读的防御性说明、重复讲解及
无关补充，让问答检验实际推理，并在原有一次校订中检查 Markdown 加粗标签边界。

## Skill 的输入、中间文件和输出结构

以笔记总根目录作为 Obsidian 仓库，`.obsidian/` 保留在该层。每门课程有独立的
`input/`、`output/` 和 `workspace/`；助手命令的 `--root` 指向课程目录，而非仓库总根目录。
课程清单用于明确讲义与转录配对及讲次顺序；显式材料路径仍受支持，无需移动原件。

```text
<笔记根目录>/                                      Obsidian 仓库总根目录
  .obsidian/                                    原有配置
  computer-organization-and-architecture/        课程目录（--root）
    input/course.yaml                           可选课程清单
    input/L02/                                  讲义和转录
    workspace/L02/<run-id>/                      原始材料、计划、任务请求、章节回答、
                                                读图、初稿、校订、最终 JSON 和回答缓存
    workspace/publication/                      发布记录和修改保护
    output/index.md                             各讲目录
    output/L02/index.md                          本讲章节目录、导读和小结
    output/L02/chapters/section-1.md
    output/L02/chapters/section-2.md
    output/L02/assets/diagram.png                仅包含被引用的图片
  operating-systems/                            另一门独立课程
    input/
    output/
    workspace/
```

output/workspace 内不再重复嵌套课程 ID。新讲次目录统一为大写 `LXX`，如 `l2`、`02`
归一化为 `L02`。每节笔记包含 YAML 属性、简短编号标题、顶部和底部的上一节／下一节
导航、返回目录链接、知识讲解、例子、问答及来源脚注。
从各课程的 `output/index.md` 开始阅读，不把 output 单独打开成 Obsidian 仓库。
从独立工作区导出时，同样采用 `<仓库>/<课程目录>/output/LXX/`，必要时创建空的
input/workspace 兄弟目录，不复制原始材料或缓存，也不修改 `.obsidian/`。
直接在仓库内的课程目录生成笔记时无需另行导出。旧运行记录、缓存和手写笔记保持原路径，
不自动迁移。发布与导出继续保护手工修改，将冲突候选留在 workspace。

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
