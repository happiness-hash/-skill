import re
from collections import Counter


QUESTION_LINE_RE = re.compile(r'^\s*(\d+[\.、)]|[一二三四五六七八九十]+[、.])')
SECTION_LINE_RE = re.compile(r'^\s*[一二三四五六七八九十]+[、，].*题')
FILL_BLANK_RE = re.compile(r'_{3,}|＿{3,}|﹍{3,}')
TOPIC_MAP = {
    '医患关系': ['医患关系', '医患', '萨斯', '荷价德', '医患冲突'],
    '人体实验伦理': ['人体实验', '知情同意', '受试者', '伦理审查', '公正原则'],
    '器官移植伦理': ['器官移植', '器官捐献', '脑死亡'],
    '安乐死伦理': ['安乐死', '尊严死'],
    '代孕伦理': ['代孕', '辅助生殖', '胚胎'],
    '动物实验伦理': ['动物实验', '4R', '5F', 'replacement', 'reduction', 'refinement'],
    '心理治疗伦理': ['心理治疗', '保密', '真诚', '专业'],
    '公共卫生伦理': ['公共卫生', '封城', '强制隔离', '强制免疫', '疫情防控'],
    '生命伦理学基础': ['生命伦理', '生命质量论', '生命价值论', '生命神圣论'],
    '医学道德评价': ['医德评价', '医德', '道德评价'],
    '患者权利与义务': ['患者权利', '患者的义务', '配合诊疗', '医疗费用'],
    '医疗人际关系': ['人际关系', '医疗卫生领域', '人与组织', '人与自然环境'],
}


def estimate_text_units(text):
    compact = re.sub(r'\s+', '', text)
    return len(compact)


def split_long_paragraph(paragraph, max_units=240):
    lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
    if len(lines) > 1:
        buffer = []
        current_units = 0
        for line in lines:
            line_units = estimate_text_units(line)
            if buffer and current_units + line_units > max_units:
                yield '\n'.join(buffer).strip()
                buffer = [line]
                current_units = line_units
            else:
                buffer.append(line)
                current_units += line_units
        if buffer:
            yield '\n'.join(buffer).strip()
        return

    sentences = [sentence.strip() for sentence in re.split(r'(?<=[。！？!?])\s*', paragraph) if sentence.strip()]
    if not sentences:
        yield paragraph.strip()
        return

    current = []
    current_units = 0
    for sentence in sentences:
        sentence_units = estimate_text_units(sentence)
        if current and current_units + sentence_units > max_units:
            yield ''.join(current).strip()
            current = [sentence]
            current_units = sentence_units
        else:
            current.append(sentence)
            current_units += sentence_units
    if current:
        yield ''.join(current).strip()


def split_text_into_blocks(text, max_words=120):
    return list(stream_blocks_from_paragraphs(re.split(r'\n\s*\n', text), max_words=max_words)) or [text.strip()]


def is_fill_blank_piece(text):
    return '填空题' in text or len(FILL_BLANK_RE.findall(text)) >= 2


def stream_blocks_from_paragraphs(paragraphs, max_words=120):
    max_units = max_words * 2
    current_block = []
    current_units = 0

    for raw_paragraph in paragraphs:
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue

        pieces = list(split_long_paragraph(paragraph, max_units=max_units))
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            piece_units = estimate_text_units(piece)
            starts_new_question = bool(QUESTION_LINE_RE.match(piece) or SECTION_LINE_RE.match(piece))
            fill_blank_piece = is_fill_blank_piece(piece)

            if fill_blank_piece:
                if current_block:
                    yield '\n\n'.join(current_block).strip()
                    current_block = []
                    current_units = 0
                yield piece
                continue

            if current_block and (
                current_units + piece_units > max_units
                or starts_new_question and current_units >= max_units * 0.55
                or is_fill_blank_piece('\n\n'.join(current_block))
            ):
                yield '\n\n'.join(current_block).strip()
                current_block = [piece]
                current_units = piece_units
            else:
                current_block.append(piece)
                current_units += piece_units

    if current_block:
        yield '\n\n'.join(current_block).strip()


def extract_topic_keywords(text, limit=6):
    candidates = []
    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        if clean_line.startswith('=== Page'):
            continue
        if re.match(r'^[A-EＡ-Ｅ][\.．、\s]', clean_line):
            continue
        if clean_line.startswith('答案'):
            continue
        candidates.extend(re.findall(r'[\u4e00-\u9fff]{2,12}', clean_line))

    filtered = [
        word for word in candidates
        if word not in {'选择题', '填空题', '简述题', '案例分析题', '单项选择题', '多项选择题', '知识点', '原始内容', '归纳摘要'}
    ]
    most_common = [word for word, _ in Counter(filtered).most_common(limit)]
    return most_common


def infer_course_topics(text, limit=6):
    matches = []
    lowered = text.lower()
    for topic, keywords in TOPIC_MAP.items():
        hit_count = 0
        for keyword in keywords:
            if keyword.lower() in lowered:
                hit_count += 1
        if hit_count:
            matches.append((topic, hit_count))

    matches.sort(key=lambda item: (-item[1], item[0]))
    topics = [topic for topic, _ in matches[:limit]]
    if topics:
        return topics
    return extract_topic_keywords(text, limit=limit)


def detect_question_types(text):
    types = []
    if '单项选择题' in text:
        types.append('单项选择题')
    if '多项选择题' in text:
        types.append('多项选择题')
    if '填空题' in text:
        types.append('填空题')
    if '简述题' in text or '简答题' in text:
        types.append('简述题')
    if '案例分析题' in text:
        types.append('案例分析题')
    return types


def extract_fill_blank_prompts(text, limit=4):
    prompts = []
    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        if '填空题' in clean_line:
            continue
        if FILL_BLANK_RE.search(clean_line):
            prompts.append(clean_line)
    return prompts[:limit]


def extract_representative_questions(text, limit=3):
    questions = []
    for line in text.splitlines():
        clean_line = line.strip()
        if QUESTION_LINE_RE.match(clean_line) and len(clean_line) >= 6:
            questions.append(clean_line)
    return questions[:limit]


def build_question_bank_summary(text):
    question_types = detect_question_types(text)
    keywords = infer_course_topics(text)
    sample_questions = extract_representative_questions(text)
    lines = []

    if '填空题' in question_types or is_fill_blank_piece(text):
        fill_blank_prompts = extract_fill_blank_prompts(text)
        lines.append('题型：填空题')
        if keywords:
            lines.append('填空主题：' + '、'.join(keywords))
        if fill_blank_prompts:
            lines.append('待填知识点：')
            for prompt in fill_blank_prompts:
                lines.append(f'- {prompt}')
        return '\n'.join(lines).strip()

    if question_types:
        lines.append('题型：' + '、'.join(question_types))
    if keywords:
        lines.append('知识点：' + '、'.join(keywords))
    if sample_questions:
        lines.append('代表题目：')
        for question in sample_questions:
            lines.append(f'- {question}')
    return '\n'.join(lines).strip()


def simple_summary(text, max_sentences=3):
    structured_summary = build_question_bank_summary(text)
    if structured_summary:
        return structured_summary

    sentences = [sentence.strip() for sentence in re.split(r'(?<=[。！？!?])\s*', text) if sentence.strip()]
    if not sentences:
        return text.strip()[:300]

    summary_sentences = sentences[:max_sentences]
    words = [word for word in re.findall(r'[\u4e00-\u9fffA-Za-z0-9_]{2,}', text) if len(word) > 1]
    most_common = [word for word, _ in Counter(words).most_common(5)]
    keyword_line = '；'.join(most_common)
    return ' '.join(summary_sentences) + (f' 知识点：{keyword_line}' if most_common else '')
