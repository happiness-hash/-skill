import unittest

from exam_analysis.question_generation import extract_original_questions
from exam_analysis.text_processing import simple_summary, split_text_into_blocks


class TextProcessingTests(unittest.TestCase):
    def test_split_text_into_blocks_splits_large_text(self):
        text = "第一段内容很多很多很多。\n\n第二段内容也很多很多很多。"
        blocks = split_text_into_blocks(text, max_words=2)
        self.assertGreaterEqual(len(blocks), 1)
        self.assertIn("第一段内容很多很多很多。", blocks[0])

    def test_simple_summary_returns_text_and_keywords(self):
        text = "代数是数学的一部分。代数关注方程和变量。代数也用于建模。"
        summary = simple_summary(text)
        self.assertIn("代数", summary)

    def test_extract_original_questions_finds_numbered_questions(self):
        text = "1. 什么是医学伦理？\n答案略\n2. 简述医患关系模式。"
        questions = extract_original_questions(text)
        self.assertEqual(len(questions), 2)
        self.assertIn("1. 什么是医学伦理？", questions)


if __name__ == '__main__':
    unittest.main()
