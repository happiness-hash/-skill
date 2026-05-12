import re
from collections import Counter


def split_long_paragraph(paragraph, max_words=120):
    sentences = re.split(r'(?<=[。！？!?])\s*', paragraph)
    parts = []
    current = []
    current_words = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = len(sentence.split())
        if current_words + words > max_words and current:
            parts.append(''.join(current).strip())
            current = [sentence]
            current_words = words
        else:
            current.append(sentence)
            current_words += words
    if current:
        parts.append(''.join(current).strip())
    return parts


def split_text_into_blocks(text, max_words=120):
    paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n', text) if paragraph.strip()]
    blocks = []
    current_block = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph_words = len(paragraph.split())
        pieces = split_long_paragraph(paragraph, max_words) if paragraph_words > max_words else [paragraph]

        for piece in pieces:
            piece_words = len(piece.split())
            if current_block and current_words + piece_words > max_words:
                blocks.append('\n\n'.join(current_block).strip())
                current_block = [piece]
                current_words = piece_words
            else:
                current_block.append(piece)
                current_words += piece_words

    if current_block:
        blocks.append('\n\n'.join(current_block).strip())

    return blocks or [text.strip()]


def simple_summary(text, max_sentences=3):
    sentences = [sentence.strip() for sentence in re.split(r'(?<=[。！？!?])\s*', text) if sentence.strip()]
    if not sentences:
        return text.strip()[:300]

    summary_sentences = sentences[:max_sentences]
    words = [word for word in re.findall(r'\w+', text) if len(word) > 3]
    most_common = [word for word, _ in Counter(words).most_common(5)]
    keyword_line = '；'.join(most_common)
    return ' '.join(summary_sentences) + (f' 知识点：{keyword_line}' if most_common else '')
