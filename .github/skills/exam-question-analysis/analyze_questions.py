import argparse
import os
import sys

from exam_analysis.config import DEFAULT_OPENAI_MODEL, build_openai_config
from exam_analysis.pipeline import run_analysis


def render_progress_bar(progress, width=28):
    progress = max(0, min(100, int(progress)))
    filled = int(width * progress / 100)
    return '[' + ('#' * filled) + ('-' * (width - filled)) + f'] {progress:>3}%'


def build_parser():
    parser = argparse.ArgumentParser(description='对上传的试卷图片进行OCR分块分析，生成节点文件、全文总结、模拟试卷和答案')
    parser.add_argument('folder', help='包含试卷图片的文件夹路径')
    parser.add_argument('--output-dir', '-d', required=True, help='输出结果目录，必须显式指定')
    parser.add_argument('--num-questions', '-n', type=int, default=5, help='生成模拟试卷的套数')
    parser.add_argument('--no-openai', action='store_true', help='不使用OpenAI API，仅使用本地规则生成摘要和题目')
    parser.add_argument('--use-multimodal-ocr', action='store_true', help='使用OpenAI多模态模型进行OCR提取')
    parser.add_argument('--api-key', help='可选，显式指定 OpenAI API Key；未提供时回退到 OPENAI_API_KEY')
    parser.add_argument('--base-url', help='可选，指定 OpenAI 兼容接口的 Base URL；未提供时回退到 OPENAI_BASE_URL')
    parser.add_argument('--model', default=None, help=f'可选，文本总结与出题模型；默认 {DEFAULT_OPENAI_MODEL} 或 OPENAI_MODEL')
    parser.add_argument('--vision-model', default=None, help=f'可选，多模态OCR模型；默认 {DEFAULT_OPENAI_MODEL} 或 OPENAI_VISION_MODEL/--model')
    parser.add_argument('--chunk-size', type=int, default=120, help='每个叶子节点块的最大词数')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    folder_path = args.folder
    if not os.path.isdir(folder_path):
        print('错误：无效的文件夹路径')
        sys.exit(1)

    openai_config = build_openai_config(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        vision_model=args.vision_model,
    )

    use_multimodal_ocr = args.use_multimodal_ocr and bool(openai_config.get('api_key'))
    if args.use_multimodal_ocr and not use_multimodal_ocr:
        print('错误：已请求多模态OCR，但未提供 OpenAI API Key。请设置 OPENAI_API_KEY 或传入 --api-key。')
        sys.exit(1)

    use_ai = not args.no_openai and bool(openai_config.get('api_key'))
    if not use_ai:
        print('未启用OpenAI，使用本地规则进行摘要和题目生成。')
    elif openai_config.get('base_url'):
        print(f"已启用 OpenAI 兼容接口，Base URL: {openai_config['base_url']}")
    print(f"文本模型: {openai_config['model']}")
    if use_multimodal_ocr:
        print(f"视觉模型: {openai_config['vision_model']}")

    last_progress = {'value': -1, 'detail': ''}

    def on_progress(event):
        progress_value = event['progress']
        detail = event.get('detail', '')
        if progress_value == last_progress['value'] and detail == last_progress['detail']:
            return
        last_progress['value'] = progress_value
        last_progress['detail'] = detail
        line = f"\r{render_progress_bar(progress_value)} {detail}"
        print(line[:180].ljust(180), end='', flush=True)

    try:
        result = run_analysis(
            folder_path=folder_path,
            output_dir=args.output_dir,
            num_questions=args.num_questions,
            chunk_size=args.chunk_size,
            use_ai=use_ai,
            use_multimodal_ocr=use_multimodal_ocr,
            openai_config=openai_config,
            progress_callback=on_progress,
        )
    except ValueError as exc:
        print()
        print(f'错误：{exc}')
        sys.exit(1)
    print()

    print(f"共生成 {len(result['blocks'])} 个块，线段树高度约为 {result['tree_height']} 层")
    print('\n处理完成！')
    print(f"输出目录: {args.output_dir}")
    print(f"- 叶子与节点摘要文件: {len(result['node_files'])} 个，保存于 {result['summaries_dir']}")
    print(f"- 目录文件: {result['toc_path']}")
    print(f"- 全文总结: {result['full_summary_path']}")
    print(f"- 模拟试卷: {result['questions_path']}")
    print(f"- 答案文件: {len(result['answer_files'])} 个，保存于 {result['answers_dir']}")
    print(f"- 模拟试卷答案总览: {result['mock_answer_overview_path']}")
    print(f"- 原题整理: {result['original_questions_path']}")
    print(f"- 原题答案文件: {len(result['original_answer_files'])} 个，保存于 {os.path.join(result['answers_dir'], 'original_questions')}")
    print(f"- 原题答案总览: {result['original_answer_overview_path']}")


if __name__ == '__main__':
    main()
