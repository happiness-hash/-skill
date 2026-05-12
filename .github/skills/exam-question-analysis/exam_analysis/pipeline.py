import math
import os

from .ocr import extract_text_from_images
from .output_writer import create_full_summary, create_table_of_contents, save_answer_overview, save_original_questions, save_questions
from .question_generation import extract_original_questions, generate_original_question_answers, generate_questions_and_answers
from .summarization import build_segment_tree
from .text_processing import split_text_into_blocks


def run_analysis(folder_path, output_dir, num_questions, chunk_size, use_ai, use_multimodal_ocr, openai_config):
    summaries_dir = os.path.join(output_dir, 'summaries')
    answers_dir = os.path.join(output_dir, 'answers')
    os.makedirs(summaries_dir, exist_ok=True)
    os.makedirs(answers_dir, exist_ok=True)

    text = extract_text_from_images(
        folder_path,
        use_multimodal=use_multimodal_ocr,
        multimodal_model=openai_config['vision_model'],
        openai_config=openai_config,
    )
    if not text.strip():
        raise ValueError('未提取到文本')

    blocks = split_text_into_blocks(text, max_words=chunk_size)
    root_summary, node_files = build_segment_tree(
        blocks,
        summaries_dir,
        0,
        len(blocks) - 1,
        0,
        use_ai=use_ai,
        openai_config=openai_config,
    )
    toc_path = create_table_of_contents(output_dir, node_files)
    full_summary_path = create_full_summary(output_dir, root_summary, node_files)
    questions, answers, answer_files = generate_questions_and_answers(
        root_summary,
        num_questions,
        answers_dir,
        use_ai=use_ai,
        openai_config=openai_config,
    )
    original_questions = extract_original_questions(text)
    original_questions_path = save_original_questions(output_dir, original_questions)
    original_answers, original_answer_files = generate_original_question_answers(
        original_questions,
        text,
        answers_dir,
        use_ai=use_ai,
        openai_config=openai_config,
    )
    questions_path = save_questions(output_dir, questions)
    mock_answer_overview_path = save_answer_overview(
        os.path.join(output_dir, 'mock_exam_answers.md'),
        '模拟题答案总览',
        questions,
        answers,
    )
    original_answer_overview_path = save_answer_overview(
        os.path.join(output_dir, 'original_question_answers.md'),
        '原题答案总览',
        original_questions,
        original_answers,
    )

    return {
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
        'summaries_dir': summaries_dir,
        'answers_dir': answers_dir,
        'tree_height': math.ceil(math.log2(len(blocks) + 1)),
    }
