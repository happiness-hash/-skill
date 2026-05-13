import html
import json
import os
import re


NODE_FILE_RE = re.compile(r'^level_(\d+)_(\d+)_(\d+)\.md$')


def _read_text(path):
    with open(path, 'r', encoding='utf-8') as file_obj:
        return file_obj.read()


def _extract_section(content, heading):
    pattern = re.compile(rf'^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)', re.MULTILINE | re.DOTALL)
    match = pattern.search(content)
    return match.group(1).strip() if match else ''


def _first_sentence(text, max_length=120):
    clean_text = re.sub(r'\s+', ' ', text).strip()
    if len(clean_text) <= max_length:
        return clean_text
    return clean_text[:max_length].rstrip() + '...'


def parse_summary_node(path, summaries_dir):
    filename = os.path.basename(path)
    match = NODE_FILE_RE.match(filename)
    if not match:
        return None

    content = _read_text(path)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    summary = _extract_section(content, '归纳摘要')
    children_text = _extract_section(content, '子节点')
    child_files = [
        line.lstrip('-').strip()
        for line in children_text.splitlines()
        if line.strip().startswith('-')
    ]

    level, start, end = (int(part) for part in match.groups())
    return {
        'id': filename,
        'title': title_match.group(1).strip() if title_match else filename,
        'level': level,
        'start': start,
        'end': end,
        'range': f'{start}-{end}',
        'summary': summary,
        'overview': _first_sentence(summary),
        'children': [os.path.basename(child) for child in child_files],
        'file': os.path.relpath(path, summaries_dir),
    }


def build_tree_index(node_files, summaries_dir):
    nodes = {}
    for path in node_files:
        node = parse_summary_node(path, summaries_dir)
        if node:
            nodes[node['id']] = node

    child_ids = {child for node in nodes.values() for child in node['children']}
    root_candidates = [node_id for node_id in nodes if node_id not in child_ids]
    root_id = sorted(root_candidates, key=lambda node_id: (nodes[node_id]['level'], nodes[node_id]['start']))[0] if root_candidates else None
    return {
        'root_id': root_id,
        'nodes': nodes,
    }


def save_tree_overview_json(output_dir, tree_index):
    path = os.path.join(output_dir, 'segment_tree_overview.json')
    with open(path, 'w', encoding='utf-8') as file_obj:
        json.dump(tree_index, file_obj, ensure_ascii=False, indent=2)
    return path


def _render_node_html(node, nodes):
    children_html = ''.join(
        _render_node_html(nodes[child_id], nodes)
        for child_id in node['children']
        if child_id in nodes
    )
    details_attr = ' open' if node['level'] <= 1 else ''
    summary_html = html.escape(node['overview'] or '暂无概要')
    title_html = html.escape(node['title'])
    file_html = html.escape(node['file'])
    range_html = html.escape(node['range'])
    return (
        f'<li>'
        f'<details{details_attr}>'
        f'<summary><span class="node-title">{title_html}</span>'
        f'<span class="node-meta">层级 {node["level"]} · 块 {range_html}</span></summary>'
        f'<p>{summary_html}</p>'
        f'<a href="summaries/{file_html}">查看节点文件</a>'
        f'{"<ol>" + children_html + "</ol>" if children_html else ""}'
        f'</details>'
        f'</li>'
    )


def save_tree_visualization_html(output_dir, tree_index):
    path = os.path.join(output_dir, 'segment_tree_visualization.html')
    nodes = tree_index['nodes']
    root_id = tree_index.get('root_id')
    body = _render_node_html(nodes[root_id], nodes) if root_id in nodes else '<li>未找到线段树节点</li>'
    html_text = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>线段树摘要可视化</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      color: #1f2933;
      background: linear-gradient(180deg, #f3f7fb 0%, #ffffff 100%);
    }}
    h1 {{ margin-top: 0; }}
    .shell {{ max-width: 1120px; margin: 0 auto; }}
    ol {{ list-style: none; padding-left: 28px; border-left: 1px solid #d8e1ec; }}
    li {{ margin: 12px 0; }}
    details {{
      background: #ffffff;
      border: 1px solid #d8e1ec;
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 8px 20px rgba(31, 41, 51, 0.05);
    }}
    summary {{ cursor: pointer; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    .node-title {{ font-weight: 700; }}
    .node-meta {{ color: #65758b; font-size: 13px; }}
    p {{ margin: 10px 0; line-height: 1.7; }}
    a {{ color: #1d6fdc; text-decoration: none; font-size: 14px; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main class="shell">
    <h1>线段树摘要可视化</h1>
    <ol>{body}</ol>
  </main>
</body>
</html>'''
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(html_text)
    return path


def create_tree_visualization(output_dir, summaries_dir, node_files):
    tree_index = build_tree_index(node_files, summaries_dir)
    json_path = save_tree_overview_json(output_dir, tree_index)
    html_path = save_tree_visualization_html(output_dir, tree_index)
    return json_path, html_path
