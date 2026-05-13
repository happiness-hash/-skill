import os
import zipfile


EXCLUDED_ARCHIVE_DIRS = {'.git', '.idea', '.venv', '__pycache__'}
EXCLUDED_ARCHIVE_SUFFIXES = {'.pyc', '.pyo'}


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


def save_page_text(output_dir, page_number, filename, page_text):
    pages_dir = os.path.join(output_dir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    path = os.path.join(pages_dir, f'page_{page_number:03d}.txt')
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(f'=== Page {page_number}: {filename} ===\n')
        file_obj.write(page_text.strip() + '\n')
    return path


def save_block_file(output_dir, block_number, block_text):
    blocks_dir = os.path.join(output_dir, 'blocks')
    os.makedirs(blocks_dir, exist_ok=True)
    path = os.path.join(blocks_dir, f'block_{block_number:03d}.txt')
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(block_text.strip() + '\n')
    return path


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
        file_obj.write('# 模拟试卷\n\n')
        for question in questions:
            file_obj.write(question.rstrip() + '\n\n')
    return questions_path


def save_original_questions(output_dir, questions):
    questions_path = os.path.join(output_dir, 'original_questions.txt')
    with open(questions_path, 'w', encoding='utf-8') as file_obj:
        file_obj.write('# 原题整理\n\n')
        for question in questions:
            file_obj.write(question + '\n')
    return questions_path


def save_answer_overview(path, title, questions, answers):
    with open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(f'# {title}\n\n')
        for index, question in enumerate(questions, 1):
            answer = answers[index - 1] if index - 1 < len(answers) else '暂无答案'
            file_obj.write(f'## 第{index}题\n\n')
            file_obj.write(f'**题目**\n\n{question}\n\n')
            file_obj.write(f'**答案**\n\n{answer}\n\n')
    return path


def create_output_archive(output_dir, archive_name='analysis_outputs.zip'):
    archive_path = os.path.join(output_dir, archive_name)
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for root, dirs, files in os.walk(output_dir):
            dirs[:] = [dirname for dirname in dirs if dirname not in EXCLUDED_ARCHIVE_DIRS]
            for filename in files:
                path = os.path.join(root, filename)
                if path == archive_path:
                    continue
                if os.path.splitext(filename)[1].lower() in EXCLUDED_ARCHIVE_SUFFIXES:
                    continue
                relative_path = os.path.relpath(path, output_dir)
                if any(part in EXCLUDED_ARCHIVE_DIRS for part in relative_path.split(os.sep)):
                    continue
                archive.write(path, relative_path)
    return archive_path
