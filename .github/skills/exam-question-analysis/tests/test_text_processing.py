import unittest

from exam_analysis.question_generation import extract_original_questions
from exam_analysis.text_processing import simple_summary, split_text_into_blocks


class TextProcessingTests(unittest.TestCase):
    def test_split_text_into_blocks_splits_large_text(self):
        text = "1. 第一题内容很多很多很多很多很多很多。\nA. 选项一\n\n2. 第二题内容也很多很多很多很多很多很多。\nB. 选项二"
        blocks = split_text_into_blocks(text, max_words=10)
        self.assertGreaterEqual(len(blocks), 2)
        self.assertIn("1. 第一题", blocks[0])

    def test_split_text_into_blocks_isolates_fill_blank_section(self):
        text = "多项选择题\n1. 第一题。\n\n填空题\n1. 动物实验的5F原则包括______、环境福利、______。\n2. 人体实验原则包括______、公正原则、______。\n\n简述题\n1. 什么是安乐死？"
        blocks = split_text_into_blocks(text, max_words=80)
        fill_blank_blocks = [block for block in blocks if '填空题' in block or '______' in block]
        self.assertEqual(len(fill_blank_blocks), 1)
        self.assertIn("动物实验的5F原则", fill_blank_blocks[0])

    def test_simple_summary_returns_question_bank_summary(self):
        text = "单项选择题\n1. 什么是医学伦理？\nA. 选项一\n2. 简述医患关系。"
        summary = simple_summary(text)
        self.assertIn("题型：单项选择题", summary)
        self.assertIn("代表题目：", summary)

    def test_simple_summary_prefers_course_topics(self):
        text = "简述题\n1. 请简要论述安乐死的伦理争议。\n2. 说明器官移植中的伦理原则。\n3. 分析医患关系的主要影响因素。"
        summary = simple_summary(text)
        self.assertIn("安乐死伦理", summary)
        self.assertIn("器官移植伦理", summary)
        self.assertIn("医患关系", summary)

    def test_simple_summary_uses_fill_blank_format(self):
        text = "填空题\n1. 动物实验的“5F”原则包括______、环境福利、______、心理福利、______。\n2. 人体实验原则包括______、______、公正原则、______、______。"
        summary = simple_summary(text)
        self.assertIn("题型：填空题", summary)
        self.assertIn("填空主题：", summary)
        self.assertIn("待填知识点：", summary)

    def test_extract_original_questions_finds_numbered_questions(self):
        text = "1. 什么是医学伦理？\n答案略\n2. 简述医患关系模式。"
        questions = extract_original_questions(text)
        self.assertEqual(len(questions), 2)
        self.assertIn("1. 什么是医学伦理？", questions)


if __name__ == '__main__':
    unittest.main()
