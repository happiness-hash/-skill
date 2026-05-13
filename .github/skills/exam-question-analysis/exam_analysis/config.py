import os

SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')
DEFAULT_OPENAI_MODEL = 'gpt-4.1-mini'
DEFAULT_OPENAI_TIMEOUT = 12000


def build_openai_config(api_key=None, base_url=None, model=None, vision_model=None):
    return {
        'api_key': api_key or os.getenv('OPENAI_API_KEY'),
        'base_url': base_url or os.getenv('OPENAI_BASE_URL'),
        'model': model or os.getenv('OPENAI_MODEL') or DEFAULT_OPENAI_MODEL,
        'vision_model': (
            vision_model
            or os.getenv('OPENAI_VISION_MODEL')
            or model
            or os.getenv('OPENAI_MODEL')
            or DEFAULT_OPENAI_MODEL
        ),
        'timeout': float(os.getenv('OPENAI_TIMEOUT') or DEFAULT_OPENAI_TIMEOUT),
    }


def get_env_status():
    return {
        'api_key': bool(os.getenv('OPENAI_API_KEY')),
        'base_url': bool(os.getenv('OPENAI_BASE_URL')),
        'model': bool(os.getenv('OPENAI_MODEL')),
        'vision_model': bool(os.getenv('OPENAI_VISION_MODEL')),
        'timeout': bool(os.getenv('OPENAI_TIMEOUT')),
    }
