import os
import threading
import uuid

from .agent_analysis import AGENT_NAMES
from .config import build_openai_config, get_env_status
from .pipeline import run_analysis


TASKS = {}
TASKS_LOCK = threading.Lock()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>考试题目分析</title>
    <style>
        :root {
            --bg: #f5f7fb;
            --card: #ffffff;
            --line: #d7dce5;
            --text: #18212f;
            --muted: #5b6472;
            --accent: #1f6feb;
            --accent-soft: #dbeafe;
            --warn-bg: #fff7e8;
            --warn-line: #f0c36d;
            --ok: #0f9d58;
            --error: #d93025;
        }
        body {
            font-family: "Segoe UI", sans-serif;
            max-width: 980px;
            margin: 32px auto;
            padding: 0 16px 48px;
            line-height: 1.6;
            color: var(--text);
            background:
                radial-gradient(circle at top right, #e0ecff 0, transparent 28%),
                linear-gradient(180deg, #f9fbff 0%, var(--bg) 100%);
        }
        .card, .notice, .warning {
            border-radius: 14px;
            padding: 18px;
            background: var(--card);
            border: 1px solid var(--line);
            box-shadow: 0 12px 30px rgba(17, 24, 39, 0.05);
        }
        .notice {
            background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
            margin-bottom: 22px;
        }
        .warning {
            background: var(--warn-bg);
            border-color: var(--warn-line);
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
            max-width: 760px;
            padding: 10px 12px;
            border: 1px solid #c8cdd8;
            border-radius: 8px;
            box-sizing: border-box;
            background: #fff;
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
            white-space: pre-wrap;
        }
        details {
            margin: 18px 0;
            padding: 12px 14px;
            border: 1px solid var(--line);
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
            background: var(--accent);
            color: white;
            font-size: 15px;
            cursor: pointer;
        }
        .status-list {
            margin: 12px 0 0;
            padding-left: 18px;
        }
        .muted {
            color: var(--muted);
        }
        .inline-check {
            margin: 10px 0;
        }
        .progress-shell {
            margin-top: 24px;
            display: none;
        }
        .progress-shell.visible {
            display: block;
        }
        .progress-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 14px;
            background: #e5eaf3;
            border-radius: 999px;
            overflow: hidden;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #1f6feb 0%, #4ea1ff 100%);
            transition: width 0.3s ease;
        }
        .progress-meta {
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            color: var(--muted);
            font-size: 14px;
        }
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-top: 18px;
        }
        .agent-card {
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 12px;
            background: #fbfdff;
        }
        .agent-card-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 8px;
        }
        .agent-name {
            font-weight: 700;
        }
        .agent-status {
            color: var(--muted);
            font-size: 13px;
        }
        .agent-task {
            margin-top: 8px;
            min-height: 38px;
            color: var(--muted);
            font-size: 13px;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 13px;
            font-weight: 600;
            background: var(--accent-soft);
            color: var(--accent);
        }
        .status-badge.done {
            background: #dcfce7;
            color: var(--ok);
        }
        .status-badge.error {
            background: #fee2e2;
            color: var(--error);
        }
        .result-panel {
            margin-top: 18px;
            display: none;
        }
        .result-panel.visible {
            display: block;
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

    <div class="card">
        <form id="analysis-form">
            <div class="field">
                <label for="folder">文件夹路径</label>
                <input type="text" id="folder" name="folder" required>
            </div>
            <div class="field">
                <label for="output_dir">输出目录</label>
                <input type="text" id="output_dir" name="output_dir" required>
            </div>
            <label class="inline-check"><input type="checkbox" name="use_multimodal_ocr" value="1"> 使用多模态 OCR</label>
            <label class="inline-check"><input type="checkbox" name="no_openai" value="1"> 禁用 OpenAI，总结和出题走本地规则</label>
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
            <button type="submit" id="submit-btn">分析</button>
        </form>

        <div id="progress-shell" class="progress-shell">
            <div class="progress-header">
                <strong>任务进度</strong>
                <span id="status-badge" class="status-badge">准备中</span>
            </div>
            <div class="progress-bar">
                <div id="progress-fill" class="progress-fill"></div>
            </div>
            <div class="progress-meta">
                <span id="progress-text">等待开始...</span>
                <span id="progress-percent">0%</span>
            </div>
            <div id="agent-grid" class="agent-grid"></div>
        </div>

        <div id="result-panel" class="result-panel">
            <h2>结果</h2>
            <pre id="result-text"></pre>
        </div>
    </div>

    <script>
        const form = document.getElementById('analysis-form');
        const submitBtn = document.getElementById('submit-btn');
        const progressShell = document.getElementById('progress-shell');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const progressPercent = document.getElementById('progress-percent');
        const agentGrid = document.getElementById('agent-grid');
        const statusBadge = document.getElementById('status-badge');
        const resultPanel = document.getElementById('result-panel');
        const resultText = document.getElementById('result-text');
        let activeTaskId = null;
        let pollTimer = null;

        function setBadge(status) {
            statusBadge.className = 'status-badge';
            if (status === 'done') {
                statusBadge.classList.add('done');
                statusBadge.textContent = '已完成';
            } else if (status === 'error') {
                statusBadge.classList.add('error');
                statusBadge.textContent = '失败';
            } else {
                statusBadge.textContent = '进行中';
            }
        }

        function renderTask(task) {
            progressShell.classList.add('visible');
            resultPanel.classList.toggle('visible', Boolean(task.result));
            progressFill.style.width = `${task.progress}%`;
            progressPercent.textContent = `${task.progress}%`;
            progressText.textContent = task.detail || task.stage || '处理中...';
            setBadge(task.status);
            renderAgents(task.agents || []);
            resultText.textContent = task.result || '';
        }

        function escapeHtml(value) {
            return String(value ?? '')
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        function renderAgents(agents) {
            const fallbackAgents = [
                { name: '水水', status: '等待中', percent: 0, current_task: '' },
                { name: '黄黄', status: '等待中', percent: 0, current_task: '' },
                { name: '向向', status: '等待中', percent: 0, current_task: '' },
            ];
            const items = agents.length ? agents : fallbackAgents;
            agentGrid.innerHTML = items.map((agent) => {
                const percent = Math.max(0, Math.min(100, Math.round(agent.percent || 0)));
                const name = escapeHtml(agent.name || 'Agent');
                const task = escapeHtml(agent.current_task || '等待任务');
                const status = escapeHtml(agent.status || '等待中');
                return `
                    <div class="agent-card">
                        <div class="agent-card-head">
                            <span class="agent-name">${name}</span>
                            <span class="agent-status">${status} · ${percent}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${percent}%"></div>
                        </div>
                        <div class="agent-task">${task}</div>
                    </div>
                `;
            }).join('');
        }

        async function pollTask(taskId) {
            try {
                const response = await fetch(`/status/${taskId}`);
                const task = await response.json();
                renderTask(task);
                if (task.status === 'running' || task.status === 'queued') {
                    pollTimer = window.setTimeout(() => pollTask(taskId), 1000);
                } else {
                    submitBtn.disabled = false;
                    activeTaskId = null;
                }
            } catch (error) {
                progressShell.classList.add('visible');
                setBadge('error');
                progressText.textContent = '获取任务状态失败';
                progressPercent.textContent = '--';
                resultPanel.classList.add('visible');
                resultText.textContent = String(error);
                submitBtn.disabled = false;
                activeTaskId = null;
            }
        }

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (pollTimer) {
                window.clearTimeout(pollTimer);
            }
            submitBtn.disabled = true;
            progressShell.classList.add('visible');
            resultPanel.classList.remove('visible');
            progressFill.style.width = '0%';
            progressPercent.textContent = '0%';
            progressText.textContent = '任务已提交，正在排队...';
            renderAgents([]);
            setBadge('queued');

            const formData = new FormData(form);
            const response = await fetch('/start', {
                method: 'POST',
                body: formData,
            });
            const payload = await response.json();
            if (!response.ok) {
                submitBtn.disabled = false;
                setBadge('error');
                progressText.textContent = payload.detail || '启动失败';
                resultPanel.classList.add('visible');
                resultText.textContent = payload.result || payload.detail || '请求失败';
                return;
            }
            activeTaskId = payload.task_id;
            pollTask(activeTaskId);
        });
    </script>
</body>
</html>
"""


def build_analysis_command(folder, output_dir, api_key, base_url, model, vision_model, use_multimodal_ocr, no_openai):
    command = ['analyze_questions.py', folder, '--output-dir', output_dir]
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


def create_task_state():
    return {
        'status': 'queued',
        'progress': 0,
        'stage': 'queued',
        'detail': '任务已创建，等待开始',
        'result': '',
        'agents': [
            {
                'name': name,
                'status': '等待中',
                'percent': 0,
                'current_task': '',
            }
            for name in AGENT_NAMES
        ],
    }


def update_task(task_id, **updates):
    with TASKS_LOCK:
        task = TASKS.setdefault(task_id, create_task_state())
        task.update(updates)


def get_task(task_id):
    with TASKS_LOCK:
        return dict(TASKS.get(task_id, create_task_state()))


def format_success_result(result, output_dir):
    lines = [
        '处理完成！',
        f'输出目录: {output_dir}',
        f"- 叶子与节点摘要文件: {len(result['node_files'])} 个，保存于 {result['summaries_dir']}",
        f"- 目录文件: {result['toc_path']}",
        f"- 全文总结: {result['full_summary_path']}",
        f"- 线段树节点概要: {result['tree_overview_path']}",
        f"- 线段树可视化: {result['tree_visualization_path']}",
        f"- 三 Agent 分组概要: {result['agent_group_summary_path']}",
        f"- 三 Agent 分析文件: {len(result['agent_report_files'])} 个",
        f"- 三 Agent 工作进度数据: {result['agent_progress_json_path']}",
        f"- 三 Agent 工作进度可视化: {result['agent_progress_html_path']}",
        f"- 模拟试卷: {result['questions_path']}",
        f"- 答案文件: {len(result['answer_files'])} 个，保存于 {result['answers_dir']}",
        f"- 模拟试卷答案总览: {result['mock_answer_overview_path']}",
        f"- 原题整理: {result['original_questions_path']}",
        f"- 原题答案文件: {len(result['original_answer_files'])} 个，保存于 {os.path.join(result['answers_dir'], 'original_questions')}",
        f"- 原题答案总览: {result['original_answer_overview_path']}",
        f"- 输出压缩包: {result['archive_path']}",
    ]
    return '\n'.join(lines)


def build_task_payload(request_form):
    return {
        'folder': request_form['folder'],
        'output_dir': request_form['output_dir'],
        'api_key': request_form.get('api_key', '').strip(),
        'base_url': request_form.get('base_url', '').strip(),
        'model': request_form.get('model', '').strip(),
        'vision_model': request_form.get('vision_model', '').strip(),
        'use_multimodal_ocr': request_form.get('use_multimodal_ocr') == '1',
        'no_openai': request_form.get('no_openai') == '1',
    }


def run_analysis_task(task_id, payload):
    folder = payload['folder']
    output_dir = payload['output_dir']
    if not os.path.isdir(folder):
        update_task(task_id, status='error', progress=100, stage='error', detail='无效的文件夹路径', result='无效的文件夹路径')
        return

    openai_config = build_openai_config(
        api_key=payload['api_key'] or None,
        base_url=payload['base_url'] or None,
        model=payload['model'] or None,
        vision_model=payload['vision_model'] or None,
    )
    if payload['use_multimodal_ocr'] and not openai_config.get('api_key'):
        update_task(
            task_id,
            status='error',
            progress=100,
            stage='error',
            detail='多模态 OCR 未配置 API Key',
            result='已选择使用多模态 OCR，但当前 Web 进程未读取到 OPENAI_API_KEY。请在启动 python app.py 的同一个环境中配置 API Key，或在页面高级配置中填写 API Key。',
        )
        return

    use_multimodal_ocr = payload['use_multimodal_ocr']
    use_ai = not payload['no_openai'] and bool(openai_config.get('api_key'))

    update_task(task_id, status='running', progress=1, stage='setup', detail='任务已启动，正在准备分析')

    def on_progress(event):
        update_task(
            task_id,
            status='running',
            progress=event['progress'],
            stage=event['stage'],
            detail=event.get('detail', ''),
        )

    try:
        result = run_analysis(
            folder_path=folder,
            output_dir=output_dir,
            num_questions=5,
            chunk_size=120,
            use_ai=use_ai,
            use_multimodal_ocr=use_multimodal_ocr,
            openai_config=openai_config,
            progress_callback=on_progress,
        )
    except Exception as exc:
        update_task(task_id, status='error', progress=100, stage='error', detail='分析失败', result=str(exc))
        return

    update_task(
        task_id,
        status='done',
        progress=100,
        stage='done',
        detail='处理完成',
        result=format_success_result(result, output_dir),
    )


def start_web_analysis(request_form):
    payload = build_task_payload(request_form)
    task_id = uuid.uuid4().hex
    update_task(task_id, **create_task_state())
    thread = threading.Thread(target=run_analysis_task, args=(task_id, payload), daemon=True)
    thread.start()
    return task_id


def build_web_context():
    return {
        'env_status': get_env_status(),
    }
