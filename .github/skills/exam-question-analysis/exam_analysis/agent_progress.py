import html
import json
import os


def create_agent_progress(agent_names):
    return {
        name: {
            'name': name,
            'status': '等待中',
            'percent': 0,
            'current_task': '',
            'ocr_pages': [],
            'analysis_blocks': [],
            'completed_ocr': 0,
            'completed_analysis': 0,
            'summary': '',
        }
        for name in agent_names
    }


def update_agent(progress_state, agent_name, **updates):
    if progress_state is None:
        return
    progress_state.setdefault(agent_name, {'name': agent_name})
    progress_state[agent_name].update(updates)


def save_agent_progress_json(output_dir, progress_state):
    path = os.path.join(output_dir, 'agent_work_progress.json')
    with open(path, 'w', encoding='utf-8') as file_obj:
        json.dump({'agents': list(progress_state.values())}, file_obj, ensure_ascii=False, indent=2)
    return path


def save_agent_progress_html(output_dir, progress_state):
    path = os.path.join(output_dir, 'agent_work_progress.html')
    cards = []
    for agent in progress_state.values():
        ocr_pages = ', '.join(str(page) for page in agent.get('ocr_pages', [])) or '无'
        blocks = ', '.join(str(block) for block in agent.get('analysis_blocks', [])) or '无'
        percent = int(agent.get('percent', 0))
        cards.append(f'''
        <section class="card">
          <div class="card-head">
            <h2>{html.escape(agent.get('name', 'Agent'))}</h2>
            <span>{html.escape(agent.get('status', '等待中'))}</span>
          </div>
          <div class="bar"><div style="width: {percent}%"></div></div>
          <p class="percent">{percent}%</p>
          <dl>
            <dt>当前任务</dt><dd>{html.escape(agent.get('current_task', '') or '无')}</dd>
            <dt>OCR 页</dt><dd>{html.escape(ocr_pages)}</dd>
            <dt>分析块</dt><dd>{html.escape(blocks)}</dd>
            <dt>OCR 完成数</dt><dd>{agent.get('completed_ocr', 0)}</dd>
            <dt>分析完成数</dt><dd>{agent.get('completed_analysis', 0)}</dd>
          </dl>
          <p>{html.escape(agent.get('summary', '') or '暂无概要')}</p>
        </section>
        ''')

    html_text = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Agent 工作进度</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #1f2933;
      background: linear-gradient(180deg, #f4f8fb 0%, #ffffff 100%);
    }}
    main {{ max-width: 1160px; margin: 0 auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border: 1px solid #d8e1ec; border-radius: 8px; padding: 18px; box-shadow: 0 8px 20px rgba(31, 41, 51, 0.06); }}
    .card-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    h1 {{ margin-top: 0; }}
    h2 {{ margin: 0; }}
    .bar {{ height: 10px; background: #e5ebf2; border-radius: 999px; overflow: hidden; margin-top: 16px; }}
    .bar div {{ height: 100%; background: #2474d6; }}
    .percent {{ font-weight: 700; }}
    dl {{ display: grid; grid-template-columns: 88px 1fr; gap: 8px 12px; }}
    dt {{ color: #65758b; }}
    dd {{ margin: 0; }}
  </style>
</head>
<body>
  <main>
    <h1>Agent 工作进度</h1>
    <div class="grid">{''.join(cards)}</div>
  </main>
</body>
</html>'''
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(html_text)
    return path


def save_agent_progress(output_dir, progress_state):
    return save_agent_progress_json(output_dir, progress_state), save_agent_progress_html(output_dir, progress_state)
