import unittest

from exam_analysis.web import build_analysis_command


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


if __name__ == '__main__':
    unittest.main()
