import os


def save_node_file(path, title, raw_text, summary, child_paths):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(f'# {title}\n\n')
        file_obj.write('## 原始内容\n')
        file_obj.write(raw_text.strip() + '\n\n')
        file_obj.write('## 归纳摘要\n')
        file_obj.write(summary.strip() + '\n\n')
        if child_paths:
            file_obj.write('## 子节点\n')
            for child in child_paths:
                file_obj.write(f'- {child}\n')


def create_table_of_contents(output_dir, node_files):
    toc_path = os.path.join(output_dir, 'table_of_contents.md')
    with open(toc_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 目录\n\n')
        for path in sorted(node_files):
            file_obj.write(f'- {os.path.basename(path)}\n')
    return toc_path


def create_full_summary(output_dir, root_summary, node_files):
    full_path = os.path.join(output_dir, 'full_summary.md')
    with open(full_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 全文总结\n\n')
        file_obj.write('## 目录\n')
        for path in sorted(node_files):
            file_obj.write(f'- {os.path.basename(path)}\n')
        file_obj.write('\n## 归纳摘要\n')
        file_obj.write(root_summary.strip() + '\n')
    return full_path


def save_questions(output_dir, questions):
    questions_path = os.path.join(output_dir, 'mock_exam_questions.txt')
    with open(questions_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 模拟考试题\n\n')
        for question in questions:
            file_obj.write(question + '\n')
    return questions_path


def save_original_questions(output_dir, questions):
    questions_path = os.path.join(output_dir, 'original_questions.txt')
    with open(questions_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 原题整理\n\n')
        for question in questions:
            file_obj.write(question + '\n')
    return questions_path
