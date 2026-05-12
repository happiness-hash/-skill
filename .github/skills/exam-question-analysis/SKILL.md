---
name: exam-question-analysis
description: 分析考试题、试卷截图、练习题图片或讲义题目图片。使用这个技能来处理“把一组题目图片做OCR并整理成结构化分析”“按知识点归纳试题”“生成全文总结、目录、模拟题和答案”这类请求。支持本地 pytesseract OCR，也支持在提供 OPENAI_API_KEY 或 --api-key 时使用多模态 OCR 与 AI 总结。
---

# 考试题目分析技能

这个技能不是只负责“介绍怎么运行脚本”，而是要带着用户一步步完成整套流程：确认输入、确认 OCR 方式、确认 OpenAI 配置、执行脚本、汇报产物。涉及 `API Key`、`Base URL`、`Model`、`Vision Model` 时，默认优先建议用户通过命令行设置环境变量，以提高隐私性，避免把敏感信息直接放进命令参数或聊天内容里。

## 严格隐私限制

执行这个技能时，必须遵守下面这条硬性规则：

- 可以检查 `OPENAI_API_KEY` 是否已设置
- 不允许读取、打印、复述、转发、总结或推断 `OPENAI_API_KEY` 的具体值
- 不允许为了“验证”而把环境变量值输出到终端或聊天中
- 不允许要求用户把 `API Key` 直接粘贴到聊天里

允许的检查方式应该只返回“已设置”或“未设置”，而不是返回真实内容。

## 多 Agent 协作

这个技能可以使用 agents 协作来提高效率，尤其适合图片多、输出要求多、或者既要排障又要整理结果的场景。

推荐采用“1 个协调者 + 2 到 4 个专项 agent”的方式：

- 协调者 agent：负责和用户确认目录、OCR 路径、OpenAI 配置、最终执行命令、整合结果
- 输入检查 agent：负责检查图片目录、统计图片数量、识别是否缺图或路径错误
- 配置准备 agent：负责确认 `API Key`、`Base URL`、`Model`、`Vision Model` 的配置方式，并给出推荐命令
- 配置准备 agent：只允许检查这些配置“是否存在/是否缺失”，不允许读取或回显 `API Key` 具体值
- 结果整理 agent：在脚本执行完成后，负责读取输出目录，整理关键产物并生成面向用户的总结
- 排障 agent：仅在失败时启用，负责把错误翻译成可执行的修复建议

### 什么时候适合协作

下面这些情况建议启用 agents 协作：

- 用户要处理一整个文件夹，且图片数量较多
- 用户既要 OCR，又要总结、目录、模拟题和答案
- 用户同时要配置 OpenAI 兼容接口
- 本地 OCR 与多模态 OCR 路径都需要评估
- 执行后还要额外整理产物、解释结果或排障

### 什么时候不必协作

下面这些情况主 agent 直接完成通常更快：

- 只有一个简单目录，且用户只想直接跑一次
- 用户只是问命令怎么写
- 用户只是问某个参数是什么意思

### 协作分工原则

使用 agents 协作时，遵循这些规则：

- 主 agent 始终保留最终决策权和对用户的对话
- 不要把“立刻阻塞下一步”的工作全丢给子 agent
- 子 agent 适合做并行检查、配置梳理、结果整理、失败原因归纳
- 不要让多个 agent 改同一块配置文案或同一份结论，避免重复和冲突
- 如果只是执行一次分析脚本，主 agent 自己运行命令通常更稳妥

### 推荐协作流程

1. 协调者先确认用户的目标、图片目录、输出目录。
2. 输入检查 agent 并行检查目录是否存在、是否有图片、图片数量是否合理。
3. 配置准备 agent 并行确认用户是否需要 `API Key`、`Base URL`、`Model`、`Vision Model`。
4. 协调者根据两边结果决定走本地 OCR 还是多模态 OCR。
5. 协调者亲自执行 [analyze_questions.py](./analyze_questions.py)。
6. 结果整理 agent 读取输出目录，归纳关键文件与可继续加工的内容。
7. 如果执行失败，再启用排障 agent，总结失败原因和下一步修复建议。

### 协调者操作手册

如果你作为主 agent 执行这个技能，推荐按下面的固定节奏推进：

1. 用 1 到 2 句话复述用户目标，并说明你先检查输入目录和可用配置。
2. 如果任务复杂或用户要同时处理配置、OCR、结果整理，就启用 agents 协作。
3. 并行派发两个轻量子任务：
   - 输入检查 agent：看目录、看图片、看本地 OCR 条件
   - 配置准备 agent：看 `API Key`、`Base URL`、`Model`、`Vision Model`
4. 主 agent 不等待所有细节都回来才行动；可以先补看主脚本、准备输出目录方案。
5. 收到子 agent 结论后，主 agent 决定走本地 OCR 还是多模态 OCR。
6. 主 agent 亲自执行主命令。
7. 如执行成功，再决定是否派出结果整理 agent。
8. 如执行失败，再决定是否派出排障 agent。
9. 最后由主 agent 统一向用户汇报，不把多份零散结论直接甩给用户。

### 子 Agent 指令模板

下面这些模板可以直接复用或稍作改写。

输入检查 agent 模板：

```text
你负责 exam-question-analysis 技能的输入检查。请检查图片目录是否存在、是否包含 .png/.jpg/.jpeg、图片数量是否合理，并确认当前环境是否可直接使用本地 OCR（重点检查 tesseract 是否可用）。不要修改文件，最后给出简洁结论和检查过的路径。
```

配置准备 agent 模板：

```text
你负责 exam-question-analysis 技能的 OpenAI 配置准备。请检查当前任务是否已具备 API Key、Base URL、Model、Vision Model，并核对脚本与界面入口是否一致。只允许判断环境变量或配置项是否存在，不允许读取、打印或复述 API Key 的具体值。不要修改文件，最后说明现在若要走 API 模式还缺什么。
```

结果整理 agent 模板：

```text
你负责 exam-question-analysis 技能的结果整理。请读取输出目录中的 summaries、table_of_contents.md、full_summary.md、mock_exam_questions.txt、answers，提炼出最值得向用户汇报的内容，并指出哪些文件适合下一步继续加工。不要修改文件。
```

排障 agent 模板：

```text
你负责 exam-question-analysis 技能的排障。请根据主命令报错，判断失败发生在输入检查、OCR、OpenAI 调用、文件输出还是参数配置阶段，并给出最短修复路径。不要修改文件。
```

### 一次协作执行示例

当用户说“帮我跑这个技能，并用 API 配置一起处理”时，推荐这样推进：

1. 协调者先说明会检查图片目录和 API 配置。
2. 输入检查 agent 去确认目录里有没有图片、有没有 `tesseract`。
3. 配置准备 agent 去确认用户是否给了 `API Key`、`Base URL`、`Model`。
4. 协调者根据两边结果做判断：
   - 有 `tesseract` 且用户没要求 API：先走本地 OCR
   - 没有 `tesseract` 但用户给了 API：走多模态 OCR
   - 两边都不满足：先向用户说明缺什么
5. 协调者执行主命令。
6. 执行成功后，由结果整理 agent 归纳产物，再统一回复用户。
7. 执行失败后，由排障 agent 先归因，再统一回复用户。

## 技能目标

当用户提出下面这类需求时，使用本技能：

- 把一批题目图片做 OCR 并整理
- 按知识点归纳试卷或讲义
- 生成全文总结、目录、模拟题和答案
- 想用 API Key / Base URL / Model 配置 OpenAI 兼容接口来跑分析

主入口始终是 [analyze_questions.py](./analyze_questions.py)，只有当用户明确要网页方式时再使用 [app.py](./app.py)。

## 你要怎么引导用户

使用这个技能时，不要一上来只贴命令。要按下面顺序推进，让用户在每一步都知道接下来会发生什么。

### 第一步：确认输入目录

先确认用户提供了图片目录路径，并检查目录是否存在、是否包含 `.png`、`.jpg`、`.jpeg`。

如果启用了 agents 协作，这一步优先交给“输入检查 agent”并行完成，而协调者继续和用户确认输出目录或配置需求。

如果用户没有给目录：

- 直接提醒需要“题目图片文件夹路径”
- 如果仓库里已经有明显的测试目录或示例图片，可以说明你准备先用哪个目录演示

如果目录存在但没有图片：

- 明确告诉用户当前目录不含受支持图片
- 请用户补充图片后再运行

### 第二步：判断 OCR 路径

默认优先本地 OCR，仅在下面情况切到多模态 OCR：

- 用户明确说“用 API 跑”
- 用户要求更高 OCR 质量
- 本地 OCR 不可用
- 本地 OCR 结果明显差

判断规则：

- 如果用户提供了 `--api-key` 或环境里有 `OPENAI_API_KEY`，可以启用 AI 相关能力
- 如果用户还提供了 `base url`，就同时传入 `--base-url`
- 如果用户没有 API 配置，就优先本地 OCR
- 如果本地 `tesseract` 不可用且也没有 API 配置，要明确告诉用户当前缺少哪项条件

如果启用了 agents 协作，这一步适合由“配置准备 agent”并行收集 OpenAI 配置条件，而协调者保留最终判断。

### 第三步：确认 OpenAI 配置模式

当用户想走 API 路径时，要主动帮助用户确认配置方式，而不是默认只认环境变量。

支持三种模式：

1. 环境变量模式（默认推荐，隐私性更好）
2. 命令行显式参数模式（只在用户明确要求时使用）
3. Web 表单填写模式（适合临时调试，不适合敏感信息长期暴露）

你需要向用户说明：

- `API Key` 用于鉴权
- `Base URL` 只有在使用 OpenAI 兼容接口或代理地址时才需要
- `Model` 用于文本总结和出题
- `Vision Model` 用于多模态 OCR，通常可与文本模型相同

优先建议用户在 PowerShell 中先设置环境变量，例如：

```powershell
$env:OPENAI_API_KEY="你的_API_Key"
$env:OPENAI_BASE_URL="https://你的兼容接口/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:OPENAI_VISION_MODEL="gpt-4.1-mini"
```

然后再运行分析命令，这样可以避免把敏感值直接放进命令参数中。

如果用户说“我还要配 url”，默认理解为需要 `--base-url` 或 Web 表单里的 `Base URL`。

检查配置时，只允许确认变量是否存在，例如：

```powershell
if (Test-Path Env:OPENAI_API_KEY) { "SET" } else { "NOT_SET" }
```

不要使用会输出 `OPENAI_API_KEY` 实际内容的命令。

如果启用了 agents 协作：

- 配置准备 agent 负责整理用户已提供和缺失的配置项
- 协调者负责把这些配置转换成最终执行命令

### 第四步：构造并执行命令

不要手写重复流程，优先直接运行脚本。

这一阶段通常由协调者 agent 自己执行，不建议把真正的主命令执行交给多个 agent 竞争处理。

基础命令：

```powershell
python .github\skills\exam-question-analysis\analyze_questions.py <图片文件夹> --output-dir <输出目录>
```

使用 OpenAI 兼容接口的常见命令：

```powershell
$env:OPENAI_API_KEY="你的_API_Key"
$env:OPENAI_BASE_URL="https://你的兼容接口/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:OPENAI_VISION_MODEL="gpt-4.1-mini"
python .github\skills\exam-question-analysis\analyze_questions.py <图片文件夹> `
  --output-dir <输出目录> `
  --use-multimodal-ocr
```

补充规则：

- 始终显式传入 `--output-dir`
- 不要把结果直接写到输入目录
- 路径有空格时要加引号
- 涉及敏感 OpenAI 配置时，优先建议用户通过环境变量注入
- 用户只要求 AI 总结、不要求多模态 OCR 时，可以不加 `--use-multimodal-ocr`
- 用户要求纯本地或无法使用 API 时，加 `--no-openai`

### 第五步：解释执行结果

运行结束后，不要只说“完成了”，要明确告诉用户这些结果在哪里：

- `<输出目录>/summaries/`
- `<输出目录>/table_of_contents.md`
- `<输出目录>/full_summary.md`
- `<输出目录>/mock_exam_questions.txt`
- `<输出目录>/answers/`

如果启用了 agents 协作，这一步适合交给“结果整理 agent”先读取和归纳，再由协调者统一向用户汇报。

如果失败，也不要只贴报错。要翻译成用户能理解的原因，例如：

- 没有找到图片
- 未安装或未配置 `tesseract`
- 提供了 API Key 但没有可用的 Base URL
- 多模态 OCR 调用失败，已回退本地规则或仍需用户补充配置

如果失败且启用了 agents 协作，优先启用“排障 agent”归纳问题，再由协调者给出下一步建议。

## 典型引导话术

下面这些不是必须逐字照搬，但流程要接近。

### 场景一：用户只说“帮我跑一下”

你应该：

1. 先看是否已给图片目录
2. 如果没给，就提示需要图片目录
3. 如果仓库中已有测试图片，可说明先用测试目录演示
4. 再决定走本地 OCR 还是多模态 OCR

### 场景二：用户说“用 API Key 跑”

你应该：

1. 确认是否还需要配置 `Base URL`
2. 说明可选配置项有 `API Key`、`Base URL`、`Model`、`Vision Model`
3. 优先建议用户用 PowerShell 环境变量设置这些值
4. 只有在用户明确要求时，才退回到显式参数模式
5. 帮用户拼出命令并执行

### 场景三：用户说“我要在 skill 里一步步引导”

你应该：

1. 先确认输入目录
2. 再确认 OCR 方式
3. 再确认是否使用 OpenAI 兼容接口
4. 最后执行脚本并解释输出

重点是把决策过程说清楚，不让用户自己猜下一步。

## 参数选择策略

- 默认保留 OpenAI 总结能力；只有在用户要求纯本地运行、未配置 API Key，或网络调用不适合当前任务时，才添加 `--no-openai`
- 默认优先建议用户通过 PowerShell 环境变量设置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_VISION_MODEL`
- 当用户明确不想使用环境变量时，再传入 `--api-key`
- 当用户明确不想使用环境变量且提供了自定义 OpenAI 兼容地址时，再传入 `--base-url`
- 文本总结和出题优先使用 `--model`
- 多模态 OCR 优先使用 `--vision-model`
- 默认不要启用 `--use-multimodal-ocr`；把它视为提升 OCR 质量的可选项，而不是常规路径
- 检查 `OPENAI_API_KEY` 时，只能判断“是否已设置”，不能读取具体值

## 排障策略

- 如果本地 OCR 结果为空，先检查 Tesseract 是否可用
- 如果当前机器没有 `tesseract`，优先建议切到 API 模式
- 如果用户使用第三方 OpenAI 兼容接口，提醒其同时配置 `API Key` 和 `Base URL`
- 如果启用多模态 OCR 或 AI 总结失败，优先说明是否已经回退到本地规则
- 如果目录里没有受支持的图片，先停止执行并提示用户补充图片

## 资源

- 主入口：[analyze_questions.py](./analyze_questions.py)
- Web 界面：[app.py](./app.py)
- 安装与手工示例：[README.md](./README.md)
