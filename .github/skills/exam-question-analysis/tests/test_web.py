import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from exam_analysis.output_writer import create_output_archive, save_answer_overview
from exam_analysis.agent_analysis import run_modulo_agent_analysis, split_blocks_by_modulo
from exam_analysis.agent_progress import create_agent_progress, save_agent_progress
from exam_analysis.tree_visualization import create_tree_visualization
from exam_analysis.web import build_analysis_command, build_task_payload, create_task_state, get_task, run_analysis_task


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
        self.assertEqual([agent['name'] for agent in task['agents']], ['水水', '黄黄', '向向'])

    def test_web_multimodal_without_api_key_fails_before_local_ocr(self):
        with TemporaryDirectory() as temp_dir:
            payload = {
                'folder': temp_dir,
                'output_dir': str(Path(temp_dir) / 'output'),
                'api_key': '',
                'base_url': '',
                'model': '',
                'vision_model': '',
                'use_multimodal_ocr': True,
                'no_openai': False,
            }
            with patch.dict('os.environ', {}, clear=True):
                with patch('exam_analysis.web.run_analysis') as run_analysis:
                    run_analysis_task('missing-key-task', payload)

            task = get_task('missing-key-task')
            self.assertEqual(task['status'], 'error')
            self.assertIn('OPENAI_API_KEY', task['result'])
            run_analysis.assert_not_called()

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

    def test_create_tree_visualization_outputs_json_and_html(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            summaries_dir = output_dir / 'summaries'
            summaries_dir.mkdir()
            leaf = summaries_dir / 'level_1_1_1.md'
            root = summaries_dir / 'level_0_1_1.md'
            leaf.write_text(
                '# 叶子节点 1\n\n## 原始内容\n题目原文\n\n## 归纳摘要\n叶子概要内容。\n',
                encoding='utf-8',
            )
            root.write_text(
                '# 节点 1-1\n\n## 原始内容\n合并内容\n\n## 归纳摘要\n根节点概要内容。\n\n## 子节点\n- level_1_1_1.md\n',
                encoding='utf-8',
            )

            json_path, html_path = create_tree_visualization(
                str(output_dir),
                str(summaries_dir),
                [str(leaf), str(root)],
            )

            json_content = Path(json_path).read_text(encoding='utf-8')
            html_content = Path(html_path).read_text(encoding='utf-8')
            self.assertIn('"root_id": "level_0_1_1.md"', json_content)
            self.assertIn('根节点概要内容', html_content)
            self.assertIn('summaries/level_1_1_1.md', html_content)

    def test_agent_grouping_uses_named_agents_and_progress_visualization(self):
        groups = split_blocks_by_modulo(['a', 'b', 'c', 'd'])
        self.assertEqual(groups[0]['agent_name'], '水水')
        self.assertEqual(groups[1]['agent_name'], '黄黄')
        self.assertEqual(groups[2]['agent_name'], '向向')
        self.assertEqual([block['block_index'] for block in groups[0]['blocks']], [1, 4])

        with TemporaryDirectory() as temp_dir:
            progress_state = create_agent_progress(('水水', '黄黄', '向向'))
            result = run_modulo_agent_analysis(
                ['医学伦理学 尊重原则', '知情同意', '人体实验', '脑死亡'],
                temp_dir,
                use_ai=False,
                agent_progress=progress_state,
            )
            json_path, html_path = save_agent_progress(temp_dir, progress_state)
            html_content = Path(html_path).read_text(encoding='utf-8')

            self.assertTrue(Path(result['overview_path']).exists())
            self.assertTrue(Path(json_path).exists())
            self.assertIn('水水', html_content)
            self.assertIn('分析块', html_content)
            self.assertEqual(progress_state['水水']['analysis_blocks'], [1, 4])


if __name__ == '__main__':
    unittest.main()
