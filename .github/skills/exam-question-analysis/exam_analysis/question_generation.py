import os
import re

from .config import DEFAULT_OPENAI_MODEL
from .openai_client import get_openai_client, request_text_completion


def extract_original_questions(text):
    questions = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if re.match(r'^\d+[\.、)]', line):
            questions.append(line)
        elif re.search(r'[？?]$', line):
            questions.append(line)
    return list(dict.fromkeys(questions))


def generate_original_question_answers(original_questions, source_text, answers_dir, use_ai=True, openai_config=None):
    original_answers_dir = os.path.join(answers_dir, 'original_questions')
    os.makedirs(original_answers_dir, exist_ok=True)
    if not original_questions:
        return [], []

    answers = []
    if use_ai and get_openai_client(openai_config):
        prompt = (
            '请根据以下原始题目内容，为每一道原题给出简洁、直接的参考答案。'
            '\n\n原始材料：\n'
            f'{source_text}\n\n'
            '原题列表：\n'
            + '\n'.join(f'{index + 1}. {question}' for index, question in enumerate(original_questions))
            + '\n\n请使用如下格式输出：\n'
            '1. 题目...\n'
            '答案1: ...\n'
            '2. 题目...\n'
            '答案2: ...'
        )
        model = (openai_config or {}).get('model', DEFAULT_OPENAI_MODEL)
        text = request_text_completion(prompt, model=model, max_output_tokens=1500, openai_config=openai_config)
        if text:
            answers = [line.strip() for line in text.splitlines() if line.strip() and (line.lower().startswith('答案') or line.lower().startswith('answer'))]

    if not answers:
        for index, question in enumerate(original_questions, 1):
            answers.append(f'答案{index}: 可根据原文内容围绕“{question[:24]}”整理核心考点、定义、原理与案例分析要点。')

    answer_files = []
    for index, answer in enumerate(answers, 1):
        answer_path = os.path.join(original_answers_dir, f'original_answer_{index}.txt')
        with open(answer_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(answer + '\n')
        answer_files.append(answer_path)

    return answers, answer_files


def generate_questions_and_answers(summary, num_questions, answers_dir, use_ai=True, openai_config=None):
    os.makedirs(answers_dir, exist_ok=True)
    questions = []
    answers = []
    if use_ai and get_openai_client(openai_config):
        prompt = (
            f'请根据以下总结，生成{num_questions}道模拟考试题目，并为每道题目给出简要答案。'
            f'\n\n总结：\n{summary}\n\n'
            '请使用如下格式输出：\n'
            '1. 题目...\n'
            '答案1: ...\n'
            '2. 题目...\n'
            '答案2: ...'
        )
        model = (openai_config or {}).get('model', DEFAULT_OPENAI_MODEL)
        text = request_text_completion(prompt, model=model, max_output_tokens=1000, openai_config=openai_config)
        if text:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                if re.match(r'^\d+\.', line) or re.match(r'^\d+\)', line):
                    questions.append(line)
                elif line.lower().startswith('答案') or line.lower().startswith('answer'):
                    answers.append(line)

    if not questions:
        keywords = [word for word in re.findall(r'\w+', summary) if len(word) > 4]
        unique_keywords = list(dict.fromkeys(keywords))[:num_questions]
        for index in range(num_questions):
            topic = unique_keywords[index] if index < len(unique_keywords) else f'关键点{index+1}'
            questions.append(f'{index+1}. 请说明“{topic}”在试题中的作用。')
            answers.append(f'答案{index+1}: 这里可以归纳“{topic}”的核心考点和解题思路。')

    answer_files = []
    for index, answer in enumerate(answers, 1):
        answer_path = os.path.join(answers_dir, f'answer_{index}.txt')
        with open(answer_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(answer + '\n')
        answer_files.append(answer_path)

    return questions, answer_files
