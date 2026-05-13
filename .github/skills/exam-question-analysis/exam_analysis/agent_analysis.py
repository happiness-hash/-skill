import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .agent_progress import update_agent
from .summarization import summarize_text


AGENT_NAMES = ('水水', '黄黄', '向向')
AGENT_COUNT = len(AGENT_NAMES)


def split_blocks_by_modulo(blocks, agent_count=AGENT_COUNT):
    groups = [
        {
            'agent_id': index + 1,
            'agent_name': AGENT_NAMES[index] if index < len(AGENT_NAMES) else f'Agent {index + 1}',
            'blocks': [],
        }
        for index in range(agent_count)
    ]
    for block_index, block_text in enumerate(blocks, start=1):
        group_index = (block_index - 1) % agent_count
        groups[group_index]['blocks'].append(
            {
                'block_index': block_index,
                'text': block_text,
            }
        )
    return groups


def _build_agent_input(group):
    parts = []
    for block in group['blocks']:
        parts.append(f"### 块 {block['block_index']}\n{block['text']}")
    return '\n\n'.join(parts)


def analyze_agent_group(group, use_ai=True, openai_config=None):
    block_numbers = [str(block['block_index']) for block in group['blocks']]
    if not group['blocks']:
        return {
            'agent_id': group['agent_id'],
            'block_numbers': [],
            'summary': '该 agent 未分配到文本块。',
        }

    group_text = _build_agent_input(group)
    prompt_text = (
        f"{group['agent_name']} 负责分析块序号：{', '.join(block_numbers)}。\n\n"
        f"{group_text}\n\n"
        "请输出：1. 核心考点；2. 高频题型；3. 易错点；4. 可用于出卷的重点。"
    )
    summary = summarize_text(
        prompt_text,
        title=f"{group['agent_name']} 分组分析",
        use_ai=use_ai,
        openai_config=openai_config,
    )
    return {
        'agent_id': group['agent_id'],
        'agent_name': group['agent_name'],
        'block_numbers': block_numbers,
        'summary': summary,
    }


def save_agent_report(agents_dir, result):
    os.makedirs(agents_dir, exist_ok=True)
    path = os.path.join(agents_dir, f"agent_{result['agent_id']}_analysis.md")
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(f"# {result['agent_name']} 分组分析\n\n")
        file_obj.write("## 负责块\n\n")
        file_obj.write(', '.join(result['block_numbers']) or '无')
        file_obj.write("\n\n## 概要\n\n")
        file_obj.write(result['summary'].strip() + '\n')
    return path


def save_agent_overview(output_dir, results):
    path = os.path.join(output_dir, 'agent_group_summary.md')
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 三 Agent 分组概要\n\n')
        file_obj.write('分组规则：按文本块序号对 3 取模分配，水水、黄黄、向向三个 agent 并发分析。\n\n')
        for result in sorted(results, key=lambda item: item['agent_id']):
            file_obj.write(f"## {result['agent_name']}\n\n")
            file_obj.write(f"负责块：{', '.join(result['block_numbers']) or '无'}\n\n")
            file_obj.write(result['summary'].strip() + '\n\n')
    return path


def run_modulo_agent_analysis(blocks, output_dir, use_ai=True, openai_config=None, progress=None, agent_progress=None):
    agents_dir = os.path.join(output_dir, 'agent_analysis')
    groups = split_blocks_by_modulo(blocks)
    results = []
    report_files = []

    if progress:
        progress.emit(0, 'agent_analysis', '正在启动水水、黄黄、向向三 Agent 分组分析')

    for group in groups:
        block_numbers = [block['block_index'] for block in group['blocks']]
        update_agent(
            agent_progress,
            group['agent_name'],
            status='等待分析',
            current_task='等待块分组分析',
            analysis_blocks=block_numbers,
        )

    with ThreadPoolExecutor(max_workers=AGENT_COUNT) as executor:
        future_to_group = {
            executor.submit(analyze_agent_group, group, use_ai, openai_config): group
            for group in groups
        }
        completed = 0
        for future in as_completed(future_to_group):
            result = future.result()
            results.append(result)
            report_files.append(save_agent_report(agents_dir, result))
            completed += 1
            update_agent(
                agent_progress,
                result['agent_name'],
                status='分析完成',
                percent=100,
                current_task='块分组分析完成',
                completed_analysis=len(result['block_numbers']),
                summary=result['summary'][:180],
            )
            if progress:
                progress.emit(
                    (completed / AGENT_COUNT) * 100,
                    'agent_analysis',
                    f"已完成 {result['agent_name']} 分组分析",
                )

    results.sort(key=lambda item: item['agent_id'])
    report_files.sort()
    overview_path = save_agent_overview(output_dir, results)
    return {
        'overview_path': overview_path,
        'report_files': report_files,
        'results': results,
    }
