# 考试题目分析技能

这个技能用于分析考试题目图片，生成分析报告和类似题目。

## 安装

1. 确保Python环境已配置。
2. 安装依赖：`pip install pytesseract Pillow Flask openai`
3. 安装Tesseract OCR：从 https://github.com/UB-Mannheim/tesseract/wiki 下载并安装。
4. 设置 OpenAI 配置（可选，推荐优先使用环境变量以提高隐私性）：
   ```powershell
   $env:OPENAI_API_KEY="your_api_key_here"
   $env:OPENAI_BASE_URL="https://api.openai.com/v1"
   $env:OPENAI_MODEL="gpt-4.1-mini"
   $env:OPENAI_VISION_MODEL="gpt-4.1-mini"
   $env:OPENAI_TIMEOUT="12000"
   ```
   这样可以避免把敏感信息直接写进命令参数。只有在你明确希望这样做时，再使用 CLI 显式参数或 Web 表单填写。
   安全说明：排查配置时，推荐只检查这些环境变量是否已设置，不要输出 `OPENAI_API_KEY` 的真实内容。

## 使用

### CLI

运行脚本：

```powershell
python analyze_questions.py <文件夹路径> -d <输出目录> `
  [-n <模拟试卷套数>] `
  [--chunk-size <叶子块最大词数>] `
  [--no-openai] `
  [--use-multimodal-ocr]
```

如果你已经在当前 PowerShell 会话里设置了 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_VISION_MODEL`，脚本会自动读取这些值。

如需显式覆盖，也支持：

```powershell
python analyze_questions.py <文件夹路径> -d <输出目录> `
  [--api-key <API Key>] `
  [--base-url <Base URL>] `
  [--model <文本模型>] `
  [--vision-model <视觉模型>] `
  [--use-multimodal-ocr]
```

选项：
- `--output-dir`, `-d`: 指定输出目录，必填
- `--num-questions`, `-n`: 生成模拟试卷的套数（默认5），每套包含多种题型
- `--chunk-size`: 叶子节点块的最大词数（默认120）
- `--no-openai`: 禁用OpenAI，使用本地规则生成摘要和题目
- `--api-key`: 显式指定 API Key，未提供时回退到 `OPENAI_API_KEY`
- `--base-url`: 显式指定 OpenAI 兼容接口地址，未提供时回退到 `OPENAI_BASE_URL`
- `--model`: 文本总结与出题模型，默认 `gpt-4.1-mini`
- `--use-multimodal-ocr`: 使用OpenAI多模态模型进行OCR提取
- `--vision-model`: 多模态OCR模型名称，默认 `gpt-4.1-mini`

例如：
```powershell
python analyze_questions.py /path/to/images -d /path/to/output -n 6 --use-multimodal-ocr
```

使用自定义 API 地址与模型：
```powershell
$env:OPENAI_API_KEY="sk-xxx"
$env:OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:OPENAI_VISION_MODEL="gpt-4.1-mini"
$env:OPENAI_TIMEOUT="12000"
python analyze_questions.py /path/to/images -d /path/to/output `
  --use-multimodal-ocr
```

注意：在PowerShell中，如果路径包含空格，用引号包围：
```
python analyze_questions.py "C:\path\to\images" -d "C:\path\to\output" --use-multimodal-ocr
```

输入文件夹应包含题目图片（.png, .jpg, .jpeg）。

输出结构示例：
- `<输出目录>/summaries/`: 每个叶子节点与内部节点的单独摘要文件
- `<输出目录>/table_of_contents.md`: 目录文件
- `<输出目录>/full_summary.md`: 全文总结
- `<输出目录>/mock_exam_questions.txt`: 生成的模拟试卷
- `<输出目录>/answers/`: 对应答案文件

### Web界面

运行Web应用：

```
python app.py
```

然后在浏览器中访问 http://127.0.0.1:5000/ 。如果涉及敏感配置，优先建议先在终端设置环境变量；表单填写更适合临时调试。
页面默认会引导你使用环境变量，敏感字段也应仅在明确需要时再填写。

## 技能集成

在VS Code Copilot中，使用技能描述触发。

## Skill 调用指南

当你希望 Copilot 或支持技能的 agent 自动调用这个 skill 时，建议在请求里明确表达以下信息：

- 这是“考试题目分析”任务
- 输入是“题目图片文件夹”或“试卷截图目录”
- 你希望得到的输出类型：OCR、总结、目录、模拟试卷、原题答案、模拟试卷答案
- 你希望走 CLI 还是 Web 模式
- 是否使用 OpenAI 兼容接口

推荐触发示例：

```text
请用 exam-question-analysis skill 分析这个题目图片文件夹，先做 OCR，再输出全文总结、目录、模拟试卷和原题答案。
```

```text
请使用考试题目分析 skill，走 CLI 模式，分析这个图片目录，并把结果输出到单独目录。
```

```text
请用 exam-question-analysis skill，走 Web 模式，我想在页面里填写路径并查看分析结果。
```

```text
请用 exam-question-analysis skill，使用 OpenAI 兼容接口做多模态 OCR，并生成模拟试卷答案总览和原题答案总览。
```

调用时的推荐说法：

- “分析这个题目图片文件夹”
- “把这些试卷截图做 OCR 并整理”
- “生成总结、目录、模拟试卷和答案”
- “使用 CLI 模式”
- “使用 Web 模式”
- “使用多模态 OCR”

为了让 skill 更稳定地命中，尽量避免只说“帮我看看这个”，而不说明这是题目图片分析任务。

skill 被触发后，通常会按这个顺序推进：

1. 先确认运行模式：CLI 或 Web
2. 再确认输入图片目录和输出目录
3. 再判断走本地 OCR 还是多模态 OCR
4. 再确认是否需要 OpenAI 配置
5. 最后执行分析并汇报结果路径

## 多 Agent 协作建议

当任务较复杂时，推荐使用“协调者 + 专项 agent”的方式协作：

- 协调者：负责和用户确认目录、输出位置、OCR 路径与 OpenAI 配置，并亲自执行主命令
- 输入检查 agent：检查图片目录、图片数量、是否具备本地 OCR 条件
- 配置准备 agent：检查 `API Key`、`Base URL`、`Model`、`Vision Model`
- 结果整理 agent：读取输出目录并提炼关键产物
- 排障 agent：在失败时总结最短修复路径

推荐原则：

- 并行做检查和准备
- 主命令由协调者执行
- 最终结论由协调者统一输出
