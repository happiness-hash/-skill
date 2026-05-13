import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from exam_analysis.question_generation import extract_original_questions, generate_original_question_answers, generate_questions_and_answers
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

    def test_extract_original_questions_ignores_answer_and_summary_lines(self):
        text = (
            "答案1: 主要违背了尊重原则。知情同意的本质不是单纯签字。\n"
            "original_questtion:答案1: 可根据原文内容围绕“1.在问诊过程中，（ ）的做法是错误的”整理核心考点。\n"
            "1. 在问诊过程中，（ ）的做法是错误的\n"
            "A. 充分告知患者\n"
        )
        questions = extract_original_questions(text)
        self.assertEqual(questions, ["1. 在问诊过程中，（ ）的做法是错误的\nA. 充分告知患者"])

    def test_extract_original_questions_keeps_options_and_removes_watermarks(self):
        text = (
            "1. 下列选项中哪一项不属于脑死亡诊断标准【真·题王汇编出品】\n"
            "A. 深昏迷\n"
            "B. 自主呼吸停止\n"
            "C. 脑干反射消失\n"
            "D. 心跳完全停止\n"
            "1. 下列选项中哪一项不属于脑死亡诊断标准\n"
            "A. 深昏迷\n"
            "B. 自主呼吸停止\n"
        )
        questions = extract_original_questions(text)
        self.assertEqual(len(questions), 1)
        self.assertIn("D. 心跳完全停止", questions[0])
        self.assertNotIn("题王", questions[0])

    def test_generate_original_question_answers_keeps_multiline_answer_aligned(self):
        ai_text = (
            "1. 在问诊过程中，（ ）的做法是错误的\n"
            "答案1: 主要违背了尊重原则。\n"
            "知情同意要求医生充分告知，患者理解后自主决定。\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("exam_analysis.question_generation.get_openai_client", return_value=object()):
                with patch("exam_analysis.question_generation.request_text_completion_with_error", return_value=(ai_text, None)):
                    answers, answer_files = generate_original_question_answers(
                        ["1. 在问诊过程中，（ ）的做法是错误的"],
                        ai_text,
                        temp_dir,
                        use_ai=True,
                        openai_config={"model": "test"},
                    )

            self.assertEqual(len(answers), 1)
            self.assertIn("尊重原则", answers[0])
            self.assertIn("自主决定", answers[0])
            self.assertTrue(Path(answer_files[0]).exists())

    def test_generate_original_question_answers_reports_ai_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("exam_analysis.question_generation.get_openai_client", return_value=object()):
                with patch(
                    "exam_analysis.question_generation.request_text_completion_with_error",
                    return_value=(None, "TimeoutError: request timed out"),
                ):
                    answers, _ = generate_original_question_answers(
                        ["1. 下列哪一项不属于生命伦理四原则\nA. 尊重\nB. 公正"],
                        "",
                        temp_dir,
                        use_ai=True,
                        openai_config={"model": "test"},
                    )

            self.assertEqual(len(answers), 1)
            self.assertIn("暂未生成", answers[0])
            self.assertIn("TimeoutError", answers[0])

    def test_generate_questions_and_answers_creates_exam_sets_not_single_questions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            questions, answers, answer_files = generate_questions_and_answers(
                "医学伦理学 尊重原则 知情同意 人体实验 脑死亡 辅助生殖 公共卫生 医患关系 安乐死",
                2,
                temp_dir,
                use_ai=False,
            )

            self.assertEqual(len(questions), 2)
            self.assertEqual(len(answers), 2)
            self.assertEqual(len(answer_files), 2)
            self.assertIn("第1套模拟试卷", questions[0])
            self.assertIn("一、单项选择题", questions[0])
            self.assertIn("10.", questions[0])


if __name__ == '__main__':
    unittest.main()
