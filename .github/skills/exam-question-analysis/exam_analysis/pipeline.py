import math
import os

from .ocr import iter_image_texts
from .output_writer import create_full_summary, create_output_archive, create_table_of_contents, save_answer_overview, save_block_file, save_original_questions, save_page_text, save_questions
from .progress import ProgressTracker
from .question_generation import extract_original_questions, generate_original_question_answers, generate_questions_and_answers
from .summarization import build_segment_tree
from .text_processing import stream_blocks_from_paragraphs


def stream_pages_and_blocks(folder_path, output_dir, chunk_size, use_multimodal_ocr, openai_config, progress):
    full_text_parts = []
    paragraphs = []
    blocks = []
    block_files = []

    for item in iter_image_texts(
        folder_path,
        use_multimodal=use_multimodal_ocr,
        multimodal_model=openai_config['vision_model'],
        openai_config=openai_config,
        progress=progress,
    ):
        page_header = f"=== Page {item['index']}: {item['filename']} ==="
        page_body = item['text'].strip()
        page_text = f'{page_header}\n{page_body}'.strip()
        full_text_parts.append(page_text)
        save_page_text(output_dir, item['index'], item['filename'], page_body)
        paragraphs.extend(part.strip() for part in page_text.split('\n\n') if part.strip())

        generated_blocks = list(stream_blocks_from_paragraphs(paragraphs, max_words=chunk_size))
        if generated_blocks:
            paragraphs = [generated_blocks.pop()] if generated_blocks else paragraphs
        else:
            paragraphs = [paragraph for paragraph in paragraphs if paragraph.strip()]

        for block_text in generated_blocks:
            blocks.append(block_text)
            block_files.append(save_block_file(output_dir, len(blocks), block_text))
            progress.emit(40, 'split', f'已流式保存第 {len(blocks)} 个块')

    tail_blocks = list(stream_blocks_from_paragraphs(paragraphs, max_words=chunk_size))
    for block_text in tail_blocks:
        blocks.append(block_text)
        block_files.append(save_block_file(output_dir, len(blocks), block_text))
        progress.emit(44, 'split', f'已流式保存第 {len(blocks)} 个块')

    return '\n\n'.join(full_text_parts), blocks, block_files


def run_analysis(folder_path, output_dir, num_questions, chunk_size, use_ai, use_multimodal_ocr, openai_config, progress_callback=None):
    progress = ProgressTracker(progress_callback)
    summaries_dir = os.path.join(output_dir, 'summaries')
    answers_dir = os.path.join(output_dir, 'answers')
    os.makedirs(summaries_dir, exist_ok=True)
    os.makedirs(answers_dir, exist_ok=True)
    progress.emit(2, 'setup', '已创建输出目录')

    text, blocks, block_files = stream_pages_and_blocks(
        folder_path,
        output_dir,
        chunk_size,
        use_multimodal_ocr,
        openai_config,
        progress.child(3, 38),
    )
    if not text.strip():
        raise ValueError('未提取到文本')
    progress.emit(45, 'split', f'流式分块完成，共 {len(blocks)} 个块')
    root_summary, node_files = build_segment_tree(
        blocks,
        summaries_dir,
        0,
        len(blocks) - 1,
        0,
        use_ai=use_ai,
        openai_config=openai_config,
        progress=progress.child(46, 72),
    )
    progress.emit(74, 'outputs', '摘要完成，正在写入目录与全文总结')
    toc_path = create_table_of_contents(output_dir, node_files)
    full_summary_path = create_full_summary(output_dir, root_summary, node_files)
    questions, answers, answer_files = generate_questions_and_answers(
        root_summary,
        num_questions,
        answers_dir,
        use_ai=use_ai,
        openai_config=openai_config,
        progress=progress.child(75, 87),
    )
    progress.emit(88, 'original_questions', '模拟试卷完成，正在提取原题')
    original_questions = extract_original_questions(text)
    original_questions_path = save_original_questions(output_dir, original_questions)
    original_answers, original_answer_files = generate_original_question_answers(
        original_questions,
        text,
        answers_dir,
        use_ai=use_ai,
        openai_config=openai_config,
        progress=progress.child(89, 96),
    )
    progress.emit(97, 'outputs', '正在写入答案总览')
    questions_path = save_questions(output_dir, questions)
    mock_answer_overview_path = save_answer_overview(
        os.path.join(output_dir, 'mock_exam_answers.md'),
        '模拟试卷答案总览',
        questions,
        answers,
    )
    original_answer_overview_path = save_answer_overview(
        os.path.join(output_dir, 'original_question_answers.md'),
        '原题答案总览',
        original_questions,
        original_answers,
    )
    archive_path = create_output_archive(output_dir)
    result = {
        'text': text,
        'blocks': blocks,
        'root_summary': root_summary,
        'node_files': node_files,
        'toc_path': toc_path,
        'full_summary_path': full_summary_path,
        'questions_path': questions_path,
        'answers': answers,
        'answer_files': answer_files,
        'original_questions': original_questions,
        'original_questions_path': original_questions_path,
        'original_answers': original_answers,
        'original_answer_files': original_answer_files,
        'mock_answer_overview_path': mock_answer_overview_path,
        'original_answer_overview_path': original_answer_overview_path,
        'archive_path': archive_path,
        'summaries_dir': summaries_dir,
        'answers_dir': answers_dir,
        'block_files': block_files,
        'tree_height': math.ceil(math.log2(len(blocks) + 1)),
    }
    progress.emit(100, 'done', '处理完成')
    return result
