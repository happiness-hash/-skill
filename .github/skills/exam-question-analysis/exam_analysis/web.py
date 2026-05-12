import os
import subprocess
import sys

from .config import get_env_status


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>考试题目分析</title>
    <style>
        body {
            font-family: "Segoe UI", sans-serif;
            max-width: 900px;
            margin: 32px auto;
            padding: 0 16px 48px;
            line-height: 1.6;
        }
        .notice {
            background: #f4f8ff;
            border: 1px solid #c7dafc;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
        }
        .warning {
            background: #fff7e8;
            border: 1px solid #f0c36d;
            border-radius: 10px;
            padding: 16px;
            margin: 20px 0;
        }
        .field {
            margin-bottom: 14px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 6px;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            max-width: 720px;
            padding: 10px 12px;
            border: 1px solid #c8cdd8;
            border-radius: 8px;
            box-sizing: border-box;
        }
        code, pre {
            font-family: Consolas, monospace;
        }
        pre {
            background: #111827;
            color: #f9fafb;
            padding: 14px;
            border-radius: 10px;
            overflow-x: auto;
        }
        details {
            margin: 18px 0;
            padding: 12px 14px;
            border: 1px solid #d7dce5;
            border-radius: 10px;
            background: #fafbfc;
        }
        summary {
            cursor: pointer;
            font-weight: 600;
        }
        button {
            padding: 10px 18px;
            border: 0;
            border-radius: 8px;
            background: #1f6feb;
            color: white;
            font-size: 15px;
            cursor: pointer;
        }
        .status-list {
            margin: 12px 0 0;
            padding-left: 18px;
        }
        .muted {
            color: #4b5563;
        }
    </style>
</head>
<body>
    <h1>考试题目分析接口</h1>
    <div class="notice">
        <strong>隐私优先建议：</strong> 涉及 <code>API Key</code>、<code>Base URL</code>、<code>Model</code> 时，
        优先在启动本页面前通过 PowerShell 设置环境变量，而不是直接在网页中填写敏感信息。
        <pre>$env:OPENAI_API_KEY="你的_API_Key"
$env:OPENAI_BASE_URL="https://你的兼容接口/v1"
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:OPENAI_VISION_MODEL="gpt-4.1-mini"
python app.py</pre>
        页面提交后，分析脚本会自动读取当前会话中的这些环境变量。
        <ul class="status-list">
            <li>OPENAI_API_KEY: {{ "已设置" if env_status.api_key else "未设置" }}</li>
            <li>OPENAI_BASE_URL: {{ "已设置" if env_status.base_url else "未设置" }}</li>
            <li>OPENAI_MODEL: {{ "已设置" if env_status.model else "未设置" }}</li>
            <li>OPENAI_VISION_MODEL: {{ "已设置" if env_status.vision_model else "未设置" }}</li>
        </ul>
    </div>
    <form method="post">
        <div class="field">
            <label for="folder">文件夹路径</label>
            <input type="text" id="folder" name="folder" required>
        </div>
        <div class="field">
            <label for="output_dir">输出目录</label>
            <input type="text" id="output_dir" name="output_dir" required>
        </div>
        <label><input type="checkbox" name="use_multimodal_ocr" value="1"> 使用多模态 OCR</label>
        <br>
        <label><input type="checkbox" name="no_openai" value="1"> 禁用 OpenAI，总结和出题走本地规则</label>
        <details {% if env_status.api_key and env_status.base_url and env_status.model and env_status.vision_model %}style="display:none;"{% endif %}>
            <summary>高级配置：仅在你明确不想使用环境变量时填写</summary>
            <div class="warning">
                不推荐在页面中直接填写敏感信息。更安全的做法是先在 PowerShell 中设置环境变量，再启动本页面。
            </div>
            {% if not env_status.api_key %}
                <div class="field">
                    <label for="api_key">API Key（不推荐直接填写）</label>
                    <input type="password" id="api_key" name="api_key" autocomplete="off">
                </div>
            {% else %}
                <p class="muted">当前会话已检测到 <code>OPENAI_API_KEY</code>，因此默认不再展示 API Key 输入框。</p>
            {% endif %}
            <div class="field">
                <label for="base_url">Base URL（可选）</label>
                <input type="text" id="base_url" name="base_url" placeholder="https://api.openai.com/v1">
            </div>
            <div class="field">
                <label for="model">文本模型（可选）</label>
                <input type="text" id="model" name="model" placeholder="gpt-4.1-mini">
            </div>
            <div class="field">
                <label for="vision_model">视觉模型（可选）</label>
                <input type="text" id="vision_model" name="vision_model" placeholder="gpt-4.1-mini">
            </div>
        </details>
        <button type="submit">分析</button>
    </form>
    {% if result %}
    <h2>结果</h2>
    <pre>{{ result }}</pre>
    {% endif %}
</body>
</html>
"""


def build_analysis_command(folder, output_dir, api_key, base_url, model, vision_model, use_multimodal_ocr, no_openai):
    command = [sys.executable, 'analyze_questions.py', folder, '--output-dir', output_dir]
    if api_key:
        command.extend(['--api-key', api_key])
    if base_url:
        command.extend(['--base-url', base_url])
    if model:
        command.extend(['--model', model])
    if vision_model:
        command.extend(['--vision-model', vision_model])
    if use_multimodal_ocr:
        command.append('--use-multimodal-ocr')
    if no_openai:
        command.append('--no-openai')
    return command


def run_web_analysis(request_form, working_dir):
    folder = request_form['folder']
    output_dir = request_form['output_dir']
    api_key = request_form.get('api_key', '').strip()
    base_url = request_form.get('base_url', '').strip()
    model = request_form.get('model', '').strip()
    vision_model = request_form.get('vision_model', '').strip()
    use_multimodal_ocr = request_form.get('use_multimodal_ocr') == '1'
    no_openai = request_form.get('no_openai') == '1'

    if not os.path.isdir(folder):
        return '无效的文件夹路径'

    command = build_analysis_command(
        folder,
        output_dir,
        api_key,
        base_url,
        model,
        vision_model,
        use_multimodal_ocr,
        no_openai,
    )
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=working_dir,
    )
    return result.stdout + result.stderr


def build_web_context(result=None):
    return {
        'result': result,
        'env_status': get_env_status(),
    }
