import os

from .config import DEFAULT_OPENAI_MODEL
from .openai_client import request_text_completion
from .output_writer import save_node_file
from .text_processing import simple_summary


def openai_summary(text, title=None, openai_config=None):
    prompt = (
        '请把以下内容提炼成一个简洁的中文总结，保留关键知识点和解题思路。'
        '\n\n原文：\n' + text + '\n'
    )
    if title:
        prompt += f'\n\n标题：{title}'
    model = (openai_config or {}).get('model', DEFAULT_OPENAI_MODEL)
    return request_text_completion(prompt, model=model, max_output_tokens=700, openai_config=openai_config)


def summarize_text(text, title=None, use_ai=True, openai_config=None):
    if use_ai:
        ai_summary = openai_summary(text, title, openai_config=openai_config)
        if ai_summary:
            return ai_summary
    return simple_summary(text)


def build_segment_tree(blocks, summaries_dir, start, end, level, use_ai=True, openai_config=None):
    node_name = f'level_{level}_{start+1}_{end+1}'
    node_file = os.path.join(summaries_dir, f'{node_name}.md')

    if start == end:
        block_text = blocks[start]
        summary = summarize_text(block_text, title=f'块 {start+1}', use_ai=use_ai, openai_config=openai_config)
        save_node_file(node_file, f'叶子节点 {start+1}', block_text, summary, [])
        return summary, [node_file]

    mid = (start + end) // 2
    left_summary, left_files = build_segment_tree(blocks, summaries_dir, start, mid, level + 1, use_ai, openai_config=openai_config)
    right_summary, right_files = build_segment_tree(blocks, summaries_dir, mid + 1, end, level + 1, use_ai, openai_config=openai_config)
    merged_text = f'左子节点摘要：\n{left_summary}\n\n右子节点摘要：\n{right_summary}'
    summary = summarize_text(merged_text, title=f'节点 {start+1} 到 {end+1}', use_ai=use_ai, openai_config=openai_config)
    child_paths = [os.path.relpath(left_files[-1], summaries_dir), os.path.relpath(right_files[-1], summaries_dir)]
    save_node_file(node_file, f'节点 {start+1}-{end+1}', merged_text, summary, child_paths)
    return summary, left_files + right_files + [node_file]
