import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from exam_analysis.output_writer import create_output_archive, save_answer_overview
from exam_analysis.web import build_analysis_command, build_task_payload, create_task_state


class WebTests(unittest.TestCase):
    def test_build_analysis_command_omits_empty_optional_values(self):
        command = build_analysis_command(
            folder='input',
            output_dir='output',
            api_key='',
            base_url='',
            model='',
            vision_model='',
            use_multimodal_ocr=False,
            no_openai=False,
        )
        self.assertNotIn('--api-key', command)
        self.assertNotIn('--base-url', command)
        self.assertEqual(command[0], 'analyze_questions.py')
        self.assertEqual(command[-2:], ['--output-dir', 'output'])

    def test_build_analysis_command_includes_selected_flags(self):
        command = build_analysis_command(
            folder='input',
            output_dir='output',
            api_key='secret',
            base_url='https://example.com/v1',
            model='model-a',
            vision_model='vision-a',
            use_multimodal_ocr=True,
            no_openai=True,
        )
        self.assertIn('--api-key', command)
        self.assertIn('--use-multimodal-ocr', command)
        self.assertIn('--no-openai', command)

    def test_build_task_payload_reads_checkboxes(self):
        payload = build_task_payload(
            {
                'folder': 'input',
                'output_dir': 'output',
                'api_key': '',
                'base_url': '',
                'model': '',
                'vision_model': '',
                'use_multimodal_ocr': '1',
                'no_openai': '1',
            }
        )
        self.assertTrue(payload['use_multimodal_ocr'])
        self.assertTrue(payload['no_openai'])

    def test_create_task_state_defaults_to_queued(self):
        task = create_task_state()
        self.assertEqual(task['status'], 'queued')
        self.assertEqual(task['progress'], 0)

    def test_save_answer_overview_writes_markdown(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'answers.md'
            save_answer_overview(
                str(path),
                '测试答案总览',
                ['1. 题目A', '2. 题目B'],
                ['答案1: A', '答案2: B'],
            )
            content = path.read_text(encoding='utf-8')
            self.assertIn('# 测试答案总览', content)
            self.assertIn('## 第1题', content)
            self.assertIn('答案1: A', content)

    def test_create_output_archive_excludes_ide_and_cache_files(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / 'full_summary.md').write_text('summary', encoding='utf-8')
            (output_dir / '.idea').mkdir()
            (output_dir / '.idea' / 'workspace.xml').write_text('ide', encoding='utf-8')
            (output_dir / '__pycache__').mkdir()
            (output_dir / '__pycache__' / 'x.pyc').write_bytes(b'cache')

            archive_path = create_output_archive(str(output_dir))

            import zipfile

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())

            self.assertIn('full_summary.md', names)
            self.assertNotIn('.idea/workspace.xml', names)
            self.assertNotIn('__pycache__/x.pyc', names)


if __name__ == '__main__':
    unittest.main()
