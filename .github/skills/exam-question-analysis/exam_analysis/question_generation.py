import os
import re

from .config import DEFAULT_OPENAI_MODEL
from .openai_client import get_openai_client, request_text_completion, request_text_completion_with_error


ANSWER_LINE_RE = re.compile(r'^(答案|answer)\s*\d*\s*[:：\.、)]?', re.IGNORECASE)
NUMBERED_LINE_RE = re.compile(r'^\s*(\d+)\s*[\.\、)]\s*(.+)')
OPTION_LINE_RE = re.compile(r'^\s*[A-HＡ-Ｈ]\s*[\.\、)]\s*.+')
JUDGE_OPTION_RE = re.compile(r'^\s*(正确|错误|对|错|是|否)\s*[\.\、)]?\s*$')
QUESTION_CUE_RE = re.compile(
    r'(？|\?|（\s*）|\(\s*\)|_{2,}|____|请选择|下列|哪项|何者|简述|说明|论述|分析|判断|填空|错误|正确|不属于|属于)'
)
NON_QUESTION_PREFIX_RE = re.compile(
    r'^(答案|answer|解析|解答|参考答案|考点|原文|original_?quest\w*|summary|总结|目录|page|===|\*\*)',
    re.IGNORECASE,
)
WATERMARK_RE = re.compile(r'【[^】]*(题王|题干|汇编|出品|红袖|无偿|董|宣)[^】]*】')
SECTION_LINE_RE = re.compile(r'^(单项选择题|多项选择题|判断题|填空题|简答题|简述题|论述题|案例分析题|名词解释)\s*$')
ORIGINAL_ANSWER_BATCH_SIZE = 8
DEFAULT_QUESTIONS_PER_EXAM_SET = 10


def _strip_markdown_prefix(line):
    return re.sub(r'^\s*[-*+>]\s*', '', line).strip()


def _is_answer_line(line):
    return bool(ANSWER_LINE_RE.match(line.strip()))


def _looks_like_question(line):
    clean_line = _strip_markdown_prefix(line)
    if not clean_line or NON_QUESTION_PREFIX_RE.match(clean_line):
        return False
    if _is_answer_line(clean_line):
        return False
    if len(clean_line) < 4:
        return False
    if QUESTION_CUE_RE.search(clean_line):
        return True
    return bool(NUMBERED_LINE_RE.match(clean_line) and len(clean_line) >= 8)


def _normalize_question_line(line):
    line = WATERMARK_RE.sub('', line)
    line = re.sub(r'\s+', ' ', _strip_markdown_prefix(line)).strip()
    return line


def _dedupe_key(question):
    question = WATERMARK_RE.sub('', question)
    question = re.sub(r'^[#\s]+原题整理\s*', '', question)
    question = re.sub(r'\s+', '', question)
    question = re.sub(r'[，。,.、:：；;（）()\[\]【】“”"\'_\-—]+', '', question)
    return question.lower()


def _is_question_start(line):
    if NON_QUESTION_PREFIX_RE.match(line) or _is_answer_line(line):
        return False
    match = NUMBERED_LINE_RE.match(line)
    return bool(match and _looks_like_question(line))


def _is_question_continuation(line):
    if not line or NON_QUESTION_PREFIX_RE.match(line) or _is_answer_line(line):
        return False
    if SECTION_LINE_RE.match(line):
        return False
    return bool(
        OPTION_LINE_RE.match(line)
        or JUDGE_OPTION_RE.match(line)
        or re.match(r'^\s*[（(]?[A-HＡ-Ｈ][）)]\s*.+', line)
        or re.match(r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*.+', line)
        or re.match(r'^\s*(?:[一二三四五六七八九十]+、)\s*.+', line)
    )


def _question_stem_key(question_text):
    first_line = question_text.splitlines()[0] if question_text else question_text
    first_line = re.sub(r'^\s*\d+\s*[\.\、)]\s*', '', first_line)
    return _dedupe_key(first_line)


def _append_question_block(questions, seen, block_lines):
    clean_lines = [_normalize_question_line(line) for line in block_lines]
    clean_lines = [line for line in clean_lines if line and not WATERMARK_RE.fullmatch(line)]
    if not clean_lines:
        return

    question_text = '\n'.join(clean_lines).strip()
    if not _looks_like_question(clean_lines[0]):
        return

    key = _question_stem_key(question_text)
    if key and key not in seen:
        seen[key] = len(questions)
        questions.append(question_text)
    elif key:
        existing_index = seen[key]
        if question_text.count('\n') > questions[existing_index].count('\n'):
            questions[existing_index] = question_text


def extract_original_questions(text):
    questions = []
    seen = {}
    current_block = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        question = _normalize_question_line(line)
        if not question or NON_QUESTION_PREFIX_RE.match(question) or _is_answer_line(question):
            continue

        if _is_question_start(question):
            _append_question_block(questions, seen, current_block)
            current_block = [question]
        elif current_block and _is_question_continuation(question):
            current_block.append(question)
        elif not current_block and _looks_like_question(question):
            current_block = [question]
        elif current_block and not OPTION_LINE_RE.match(question):
            _append_question_block(questions, seen, current_block)
            current_block = []

    _append_question_block(questions, seen, current_block)
    return questions


def _iter_batches(items, batch_size):
    for start in range(0, len(items), batch_size):
        yield start, items[start:start + batch_size]


def _parse_numbered_qa_response(text, expected_count=None):
    questions_by_number = {}
    answers_by_number = {}
    current_number = None
    current_answer_lines = []

    def flush_answer():
        if current_number is not None and current_answer_lines:
            answer_text = ' '.join(current_answer_lines).strip()
            if answer_text:
                answers_by_number[current_number] = answer_text

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        answer_match = ANSWER_LINE_RE.match(line)
        if answer_match:
            flush_answer()
            number_match = re.search(r'\d+', answer_match.group(0))
            if number_match:
                current_number = int(number_match.group(0))
            elif current_number is None:
                current_number = len(answers_by_number) + 1
            current_answer_lines = [line]
            continue

        numbered_match = NUMBERED_LINE_RE.match(line)
        if numbered_match and _looks_like_question(line):
            flush_answer()
            current_number = int(numbered_match.group(1))
            current_answer_lines = []
            questions_by_number[current_number] = _normalize_question_line(line)
            continue

        if current_answer_lines:
            current_answer_lines.append(line)

    flush_answer()

    max_count = expected_count or max(
        [0] + list(questions_by_number.keys()) + list(answers_by_number.keys())
    )
    questions = [questions_by_number[index] for index in range(1, max_count + 1) if index in questions_by_number]
    answers = [answers_by_number[index] for index in range(1, max_count + 1) if index in answers_by_number]
    return questions, answers


def _parse_mock_exam_sets(text, expected_count=None):
    sets = []
    current_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                current_lines.append('')
            continue

        if re.match(r'^第\s*\d+\s*套', line):
            if current_lines:
                sets.append('\n'.join(current_lines).strip())
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        sets.append('\n'.join(current_lines).strip())

    if expected_count:
        sets = sets[:expected_count]
    return sets


def _build_local_mock_exam_set(set_index, topics):
    lines = [
        f'第{set_index}套模拟试卷',
        '',
        '一、单项选择题',
        f'1. 下列关于“{topics[0]}”的说法，哪一项最符合医学伦理学要求？',
        'A. 只考虑技术可行性',
        'B. 兼顾患者权益、风险控制与伦理规范',
        'C. 完全由医务人员单方面决定',
        'D. 只考虑效率，不考虑公平',
        f'2. 在临床情境中，涉及“{topics[1]}”时，最应优先识别的是哪类伦理原则？',
        'A. 尊重/不伤害/有利/公正等相关原则',
        'B. 行政便利原则',
        'C. 成本最低原则',
        'D. 经验优先原则',
        '',
        '二、判断题',
        f'3. 处理“{topics[2]}”相关问题时，可以忽视知情同意和伦理审查。（ ）',
        f'4. 遇到“{topics[3]}”案例，应结合规范、患者利益和社会影响综合判断。（ ）',
        '',
        '三、填空题',
        f'5. 医学伦理分析通常需要从事实、______、规范和处理建议四个方面展开。',
        f'6. 涉及“{topics[4]}”的选择题，应重点辨析题干中的关键词和限定条件。',
        '',
        '四、简答题',
        f'7. 简述“{topics[5]}”在医学伦理学中的核心考点。',
        f'8. 结合案例说明“{topics[6]}”可能涉及的伦理冲突。',
        '',
        '五、论述题',
        f'9. 试述“{topics[7]}”相关问题的分析思路。',
        f'10. 请围绕“{topics[8]}”设计一个伦理判断框架。',
    ]
    return '\n'.join(lines)


def _build_local_mock_exam_answer(set_index, topics):
    return (
        f'答案{set_index}: '
        '1.B；2.A；3.错误；4.正确；5.价值判断；6.结合题干限定条件作答。'
        f'7-10题可分别围绕“{topics[5]}”“{topics[6]}”“{topics[7]}”“{topics[8]}”'
        '展开，答题时按“概念界定、伦理原则、案例判断、处理建议”组织要点。'
    )


def generate_original_question_answers(original_questions, source_text, answers_dir, use_ai=True, openai_config=None, progress=None):
    original_answers_dir = os.path.join(answers_dir, 'original_questions')
    os.makedirs(original_answers_dir, exist_ok=True)
    if not original_questions:
        if progress:
            progress.emit(100, 'original_answers', '未识别到原题，跳过原题答案生成')
        return [], []

    answers = [''] * len(original_questions)
    client = get_openai_client(openai_config) if use_ai else None
    model = (openai_config or {}).get('model', DEFAULT_OPENAI_MODEL)

    if client:
        total = len(original_questions)
        for start, batch_questions in _iter_batches(original_questions, ORIGINAL_ANSWER_BATCH_SIZE):
            prompt = (
                '请根据以下原题逐题给出参考答案。选择题必须先给出选项字母或判断结果，'
                '再用一句话说明依据；填空题直接给出应填内容；简答/论述题给出要点。'
                '只回答本批题目，不要补充新题目。\n\n'
                '本批原题：\n'
                + '\n\n'.join(
                    f'{start + offset + 1}. {question}'
                    for offset, question in enumerate(batch_questions)
                )
                + '\n\n请严格使用如下格式输出：\n'
                '答案1: ...\n'
                '答案2: ...'
            )
            if progress:
                progress.emit(
                    5 + (start / total) * 55,
                    'original_answers',
                    f'正在生成原题答案 {start + 1}-{start + len(batch_questions)}/{total}',
                )

            text, error = request_text_completion_with_error(
                prompt,
                model=model,
                max_output_tokens=max(1200, len(batch_questions) * 220),
                openai_config=openai_config,
            )
            if text:
                _, batch_answers = _parse_numbered_qa_response(text, expected_count=len(batch_questions))
            else:
                batch_answers = []

            for offset, question in enumerate(batch_questions):
                answer_index = start + offset
                if offset < len(batch_answers) and batch_answers[offset].strip():
                    answers[answer_index] = batch_answers[offset].strip()
                else:
                    reason = error or 'AI 输出未包含对应题号答案'
                    answers[answer_index] = f'答案{answer_index + 1}: 暂未生成。原因：{reason}。题目：{question[:80]}'
    elif use_ai:
        answers = [
            f'答案{index}: 暂未生成。原因：OpenAI API key 未配置。题目：{question[:80]}'
            for index, question in enumerate(original_questions, 1)
        ]

    if not use_ai:
        answers = [
            f'答案{index}: 暂未生成。原因：当前禁用了 OpenAI，原题解析需要结合题干和选项人工或 AI 作答。题目：{question[:80]}'
            for index, question in enumerate(original_questions, 1)
        ]

    for index, question in enumerate(original_questions, 1):
        if not answers[index - 1]:
            answers[index - 1] = f'答案{index}: 暂未生成。原因：AI 输出为空。题目：{question[:80]}'

    if len(answers) > len(original_questions):
        answers = answers[:len(original_questions)]
    elif len(answers) < len(original_questions):
        for index in range(len(answers) + 1, len(original_questions) + 1):
            answers.append(f'答案{index}: 暂未生成。原因：答案数量少于题目数量。题目：{original_questions[index - 1][:80]}')

    answer_files = []
    total_answers = len(answers)
    for index, answer in enumerate(answers, 1):
        answer_path = os.path.join(original_answers_dir, f'original_answer_{index}.txt')
        with open(answer_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(answer + '\n')
        answer_files.append(answer_path)
        if progress:
            progress.emit(
                (index / total_answers) * 100,
                'original_answers',
                f'已写入原题答案 {index}/{total_answers}',
            )

    return answers, answer_files


def generate_questions_and_answers(summary, num_questions, answers_dir, use_ai=True, openai_config=None, progress=None):
    os.makedirs(answers_dir, exist_ok=True)
    questions = []
    answers = []
    if progress:
        progress.emit(10, 'mock_questions', '正在生成模拟试卷与答案')
    if use_ai and get_openai_client(openai_config):
        prompt = (
            f'请根据以下总结，生成{num_questions}套模拟试卷，每套试卷包含'
            f'{DEFAULT_QUESTIONS_PER_EXAM_SET}道题，并覆盖单选、多选、判断、填空、简答/论述等题型。'
            '每套试卷后给出对应答案。'
            f'\n\n总结：\n{summary}\n\n'
            '请使用如下格式输出：\n'
            '第1套模拟试卷\n'
            '一、单项选择题\n1. ...\n'
            '二、简答题\n...\n'
            '答案1: ...\n\n'
            '第2套模拟试卷\n'
            '...\n'
            '答案2: ...'
        )
        model = (openai_config or {}).get('model', DEFAULT_OPENAI_MODEL)
        text = request_text_completion(
            prompt,
            model=model,
            max_output_tokens=max(2500, num_questions * 900),
            openai_config=openai_config,
        )
        if text:
            questions, answers = _parse_numbered_qa_response(text, expected_count=num_questions)
            if not questions:
                questions = _parse_mock_exam_sets(text, expected_count=num_questions)
        if progress:
            progress.emit(70, 'mock_questions', '模拟试卷文本已生成，正在写入答案文件')

    if not questions:
        keywords = [word for word in re.findall(r'\w+', summary) if len(word) > 4]
        unique_keywords = list(dict.fromkeys(keywords))
        for index in range(num_questions):
            topics = [
                unique_keywords[(index * DEFAULT_QUESTIONS_PER_EXAM_SET + offset) % len(unique_keywords)]
                if unique_keywords else f'关键点{offset + 1}'
                for offset in range(DEFAULT_QUESTIONS_PER_EXAM_SET)
            ]
            questions.append(_build_local_mock_exam_set(index + 1, topics))
            answers.append(_build_local_mock_exam_answer(index + 1, topics))
        if progress:
            progress.emit(70, 'mock_questions', '已按本地规则生成模拟试卷，正在写入答案文件')

    if len(answers) < len(questions):
        for index in range(len(answers) + 1, len(questions) + 1):
            answers.append(f'答案{index}: 请结合题干对应知识点作答。')
    elif len(answers) > len(questions):
        answers = answers[:len(questions)]

    answer_files = []
    total_answers = len(answers)
    for index, answer in enumerate(answers, 1):
        answer_path = os.path.join(answers_dir, f'answer_{index}.txt')
        with open(answer_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(answer + '\n')
        answer_files.append(answer_path)
        if progress and total_answers:
            progress.emit(
                70 + (index / total_answers) * 30,
                'mock_questions',
                f'已写入模拟试卷答案 {index}/{total_answers}',
            )

    return questions, answers, answer_files
