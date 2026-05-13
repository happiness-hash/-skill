import base64
import mimetypes

from openai import OpenAI

from .config import DEFAULT_OPENAI_MODEL, build_openai_config


def get_openai_client(openai_config=None):
    openai_config = openai_config or build_openai_config()
    api_key = openai_config.get('api_key')
    if not api_key:
        return None

    client_kwargs = {'api_key': api_key}
    base_url = openai_config.get('base_url')
    if base_url:
        client_kwargs['base_url'] = base_url
    return OpenAI(**client_kwargs)


def extract_response_text(response):
    output_text = getattr(response, 'output_text', None)
    if output_text:
        return output_text.strip()

    outputs = []
    for item in getattr(response, 'output', []) or []:
        item_type = getattr(item, 'type', None)
        if item_type == 'message':
            for content in getattr(item, 'content', []) or []:
                if getattr(content, 'type', None) == 'output_text':
                    outputs.append(getattr(content, 'text', ''))
        elif item_type == 'output_text':
            outputs.append(getattr(item, 'text', ''))
    return '\n'.join(part.strip() for part in outputs if part and part.strip()).strip()


def request_text_completion_with_error(prompt, model=DEFAULT_OPENAI_MODEL, max_output_tokens=900, openai_config=None):
    client = get_openai_client(openai_config)
    if not client:
        return None, 'OpenAI API key 未配置'

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'

    text = extract_response_text(response)
    if not text:
        return None, 'OpenAI 返回为空'
    return text, None


def request_text_completion(prompt, model=DEFAULT_OPENAI_MODEL, max_output_tokens=900, openai_config=None):
    text, _ = request_text_completion_with_error(
        prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        openai_config=openai_config,
    )
    return text


def build_image_data_url(image_path):
    with open(image_path, 'rb') as file_obj:
        raw_bytes = file_obj.read()
    image_b64 = base64.b64encode(raw_bytes).decode('ascii')
    mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
    return f'data:{mime_type};base64,{image_b64}'
