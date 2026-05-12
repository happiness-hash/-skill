import os

import pytesseract
from PIL import Image

from .config import DEFAULT_OPENAI_MODEL, SUPPORTED_IMAGE_EXTENSIONS
from .openai_client import build_image_data_url, extract_response_text, get_openai_client


def local_extract_text_from_image(image_path):
    with Image.open(image_path) as img:
        return pytesseract.image_to_string(img)


def multimodal_extract_text_from_image(image_path, model=DEFAULT_OPENAI_MODEL, openai_config=None):
    client = get_openai_client(openai_config)
    if not client:
        raise RuntimeError('OPENAI_API_KEY 未设置，无法使用多模态OCR。')

    image_data = build_image_data_url(image_path)
    prompt = '请提取这张图片中的全部文字，输出纯文本，不要添加说明。'

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'input_text', 'text': prompt},
                        {'type': 'input_image', 'image_url': image_data},
                    ],
                }
            ],
            max_output_tokens=1500,
        )
        extracted = extract_response_text(response)
        if extracted:
            return extracted
    except Exception as exc:
        print(f'多模态OCR失败: {exc}，将回退到本地OCR。')

    return local_extract_text_from_image(image_path)


def extract_text_from_images(folder_path, use_multimodal=False, multimodal_model=DEFAULT_OPENAI_MODEL, openai_config=None):
    image_files = sorted(
        file_name for file_name in os.listdir(folder_path)
        if file_name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
    )
    if not image_files:
        raise ValueError('输入文件夹中没有找到支持的图片文件（.png, .jpg, .jpeg）。')

    texts = []
    for index, filename in enumerate(image_files, start=1):
        image_path = os.path.join(folder_path, filename)
        if use_multimodal:
            page_text = multimodal_extract_text_from_image(
                image_path,
                model=multimodal_model,
                openai_config=openai_config,
            )
        else:
            page_text = local_extract_text_from_image(image_path)
        texts.append(f"=== Page {index}: {filename} ===\n{page_text.strip()}")
    return '\n\n'.join(texts)
