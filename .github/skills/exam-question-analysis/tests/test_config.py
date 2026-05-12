import os
import unittest
from unittest.mock import patch

from exam_analysis.config import DEFAULT_OPENAI_MODEL, build_openai_config, get_env_status


class ConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_build_openai_config_uses_defaults(self):
        config = build_openai_config()
        self.assertIsNone(config['api_key'])
        self.assertIsNone(config['base_url'])
        self.assertEqual(config['model'], DEFAULT_OPENAI_MODEL)
        self.assertEqual(config['vision_model'], DEFAULT_OPENAI_MODEL)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'OPENAI_BASE_URL': 'https://example.com/v1', 'OPENAI_MODEL': 'model-a'}, clear=True)
    def test_build_openai_config_reads_environment(self):
        config = build_openai_config()
        self.assertEqual(config['api_key'], 'secret')
        self.assertEqual(config['base_url'], 'https://example.com/v1')
        self.assertEqual(config['model'], 'model-a')
        self.assertEqual(config['vision_model'], 'model-a')

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'secret'}, clear=True)
    def test_get_env_status_only_reports_presence(self):
        status = get_env_status()
        self.assertTrue(status['api_key'])
        self.assertFalse(status['base_url'])


if __name__ == '__main__':
    unittest.main()
