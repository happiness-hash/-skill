import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytesseract
from PIL import Image

from .agent_analysis import AGENT_NAMES
from .agent_progress import update_agent
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
        raise RuntimeError(f'多模态OCR失败: {type(exc).__name__}: {exc}') from exc

    raise RuntimeError('多模态OCR失败: 模型未返回可用文本')


def _extract_image_item(index, filename, folder_path, use_multimodal, multimodal_model, openai_config):
    image_path = os.path.join(folder_path, filename)
    if use_multimodal:
        page_text = multimodal_extract_text_from_image(
            image_path,
            model=multimodal_model,
            openai_config=openai_config,
        )
    else:
        page_text = local_extract_text_from_image(image_path)
    return {
        'index': index,
        'filename': filename,
        'text': page_text.strip(),
    }


def _iter_multimodal_image_texts_parallel(image_files, folder_path, multimodal_model, openai_config, progress=None, agent_progress=None):
    total_images = len(image_files)
    for agent_index, agent_name in enumerate(AGENT_NAMES):
        assigned_pages = [
            page_index
            for page_index in range(1, total_images + 1)
            if (page_index - 1) % len(AGENT_NAMES) == agent_index
        ]
        update_agent(
            agent_progress,
            agent_name,
            status='等待 OCR',
            percent=0,
            current_task='等待多模态 OCR',
            ocr_pages=assigned_pages,
        )

    results = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=len(AGENT_NAMES)) as executor:
        future_to_meta = {}
        for index, filename in enumerate(image_files, start=1):
            agent_name = AGENT_NAMES[(index - 1) % len(AGENT_NAMES)]
            update_agent(
                agent_progress,
                agent_name,
                status='OCR 中',
                current_task=f'准备识别第 {index} 页：{filename}',
            )
            future = executor.submit(
                _extract_image_item,
                index,
                filename,
                folder_path,
                True,
                multimodal_model,
                openai_config,
            )
            future_to_meta[future] = (index, filename, agent_name)

        for future in as_completed(future_to_meta):
            index, filename, agent_name = future_to_meta[future]
            item = future.result()
            item['total'] = total_images
            item['agent_name'] = agent_name
            results[index] = item
            completed += 1
            assigned_total = len([
                page_index
                for page_index in range(1, total_images + 1)
                if AGENT_NAMES[(page_index - 1) % len(AGENT_NAMES)] == agent_name
            ])
            completed_for_agent = len([
                page_index
                for page_index in results
                if AGENT_NAMES[(page_index - 1) % len(AGENT_NAMES)] == agent_name
            ])
            update_agent(
                agent_progress,
                agent_name,
                status='OCR 完成' if completed_for_agent == assigned_total else 'OCR 中',
                percent=int((completed_for_agent / assigned_total) * 40) if assigned_total else 40,
                current_task=f'已识别第 {index} 页：{filename}',
                completed_ocr=completed_for_agent,
            )
            if progress:
                progress.emit(
                    (completed / total_images) * 100,
                    'ocr',
                    f'{agent_name} 已完成第 {index}/{total_images} 张图片：{filename}',
                )

    for index in sorted(results):
        yield results[index]


def iter_image_texts(folder_path, use_multimodal=False, multimodal_model=DEFAULT_OPENAI_MODEL, openai_config=None, progress=None, agent_progress=None):
    image_files = sorted(
        file_name for file_name in os.listdir(folder_path)
        if file_name.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
    )
    if not image_files:
        raise ValueError('输入文件夹中没有找到支持的图片文件（.png, .jpg, .jpeg）。')

    if use_multimodal:
        yield from _iter_multimodal_image_texts_parallel(
            image_files,
            folder_path,
            multimodal_model,
            openai_config,
            progress=progress,
            agent_progress=agent_progress,
        )
        return

    total_images = len(image_files)
    for index, filename in enumerate(image_files, start=1):
        if progress:
            progress.emit(
                ((index - 1) / total_images) * 100,
                'ocr',
                f'正在识别第 {index}/{total_images} 张图片：{filename}',
            )
        item = _extract_image_item(index, filename, folder_path, False, multimodal_model, openai_config)
        if progress:
            progress.emit(
                (index / total_images) * 100,
                'ocr',
                f'已完成第 {index}/{total_images} 张图片：{filename}',
            )
        yield {
            'index': index,
            'filename': filename,
            'text': item['text'],
            'total': total_images,
        }


def extract_text_from_images(folder_path, use_multimodal=False, multimodal_model=DEFAULT_OPENAI_MODEL, openai_config=None, progress=None):
    texts = []
    for item in iter_image_texts(
        folder_path,
        use_multimodal=use_multimodal,
        multimodal_model=multimodal_model,
        openai_config=openai_config,
        progress=progress,
    ):
        texts.append(f"=== Page {item['index']}: {item['filename']} ===\n{item['text']}")
    return '\n\n'.join(texts)
