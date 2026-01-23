#!/usr/bin/env python3
"""
使用Marker服务批量处理PDF
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Tuple, Dict
import logging

# 导入配置
from config import (
    MARKER_SERVICE_URL,
    PDF_INPUT_DIR,
    MARKDOWN_OUTPUT_DIR,
    MAX_WORKERS,
    REQUEST_TIMEOUT,
    DEFAULT_LANGS
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarkerClient:
    """Marker服务客户端"""

    def __init__(self, service_url: str = MARKER_SERVICE_URL):
        self.service_url = service_url
        self.session = requests.Session()

    def check_health(self) -> bool:
        """检查服务健康状态"""
        try:
            response = self.session.get(
                f"{self.service_url}/health",
                timeout=5
            )
            if response.ok:
                return True
            return False
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

    def convert_pdf(
        self,
        pdf_path: str,
        langs: str = DEFAULT_LANGS,
        timeout: int = REQUEST_TIMEOUT
    ) -> Tuple[bool, str, Dict]:
        """
        转换单个PDF

        Args:
            pdf_path: PDF文件路径
            langs: 语言列表
            timeout: 超时时间（秒）

        Returns:
            (成功标志, Markdown文本, metadata)
        """
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': f}
                data = {'langs': langs}

                response = self.session.post(
                    f"{self.service_url}/api/convert_pdf",
                    files=files,
                    data=data,
                    timeout=timeout
                )

            if response.ok:
                result = response.json()
                if result['success']:
                    return True, result['markdown'], result['metadata']
                else:
                    logger.error(f"转换失败: {result.get('error', 'Unknown')}")
                    return False, "", {}
            else:
                logger.error(f"请求失败: {response.status_code}")
                return False, "", {}

        except Exception as e:
            logger.error(f"转换PDF失败 {pdf_path}: {e}")
            return False, "", {}


def process_single_pdf(args: Tuple[str, str, str]) -> Dict:
    """
    处理单个PDF

    Args:
        args: (pdf_path, doi, marker_service_url)

    Returns:
        处理结果字典
    """
    pdf_path, doi, marker_service_url = args

    start_time = time.time()

    # 创建客户端
    client = MarkerClient(marker_service_url)

    # 转换PDF
    success, markdown, metadata = client.convert_pdf(pdf_path)

    if not success:
        return {
            'doi': doi,
            'status': 'failed',
            'error': 'Marker转换失败',
            'duration': time.time() - start_time
        }

    # 直接保存为 PDF文件名.md（不创建文件夹）
    pdf_filename = Path(pdf_path).stem  # 获取不带扩展名的文件名
    output_path = Path(MARKDOWN_OUTPUT_DIR) / f"{pdf_filename}.md"
    
    # 确保输出目录存在
    Path(MARKDOWN_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # 保存Markdown内容
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    duration = time.time() - start_time
    logger.info(f"✅ 处理成功: {doi} → {output_path.name} ({duration:.1f}秒)")

    return {
        'doi': doi,
        'status': 'success',
        'output_path': str(output_path),
        'duration': duration
    }


def batch_process_pdfs(
    pdf_list: List[Tuple[str, str]],
    marker_service_url: str = MARKER_SERVICE_URL,
    max_workers: int = MAX_WORKERS
) -> Dict:
    """
    批量处理PDF（串行处理）

    Args:
        pdf_list: [(pdf_path, doi), ...]
        marker_service_url: Marker服务地址
        max_workers: 并发数（已废弃，保留参数兼容性）

    Returns:
        处理结果统计
    """
    logger.info("="*60)
    logger.info(f"开始批量处理PDF（串行模式）")
    logger.info(f"总数: {len(pdf_list)}")
    logger.info(f"Marker服务: {marker_service_url}")
    logger.info("="*60)

    # 检查服务健康状态
    client = MarkerClient(marker_service_url)
    if not client.check_health():
        logger.error("❌ Marker服务不可用，请检查服务是否启动")
        return {'error': 'Service unavailable'}

    logger.info("✅ Marker服务健康检查通过")

    # 串行处理
    results = []
    completed = 0
    failed = 0

    start_time = time.time()

    for pdf_path, doi in pdf_list:
        try:
            result = process_single_pdf((pdf_path, doi, marker_service_url))
            results.append(result)

            if result['status'] == 'success':
                completed += 1
            else:
                failed += 1

            # 显示进度
            total = completed + failed
            progress = (total / len(pdf_list)) * 100
            logger.info(f"进度: {total}/{len(pdf_list)} ({progress:.1f}%) - 成功:{completed} 失败:{failed}")

        except Exception as e:
            logger.error(f"❌ 任务执行失败 {doi}: {e}")
            failed += 1
            results.append({
                'doi': doi,
                'status': 'failed',
                'error': str(e)
            })

    total_time = time.time() - start_time

    # 生成统计报告
    summary = {
        'total': len(pdf_list),
        'succeeded': completed,
        'failed': failed,
        'success_rate': (completed / len(pdf_list)) * 100 if pdf_list else 0,
        'total_time': total_time,
        'avg_time_per_pdf': total_time / len(pdf_list) if pdf_list else 0,
        'results': results
    }

    # 打印总结
    logger.info("="*60)
    logger.info("批量处理完成")
    logger.info("="*60)
    logger.info(f"总数: {summary['total']}")
    logger.info(f"成功: {summary['succeeded']}")
    logger.info(f"失败: {summary['failed']}")
    logger.info(f"成功率: {summary['success_rate']:.1f}%")
    logger.info(f"总耗时: {summary['total_time']:.1f}秒")
    logger.info(f"平均耗时: {summary['avg_time_per_pdf']:.1f}秒/PDF")
    logger.info("="*60)

    # 保存报告
    report_path = Path(MARKDOWN_OUTPUT_DIR) / 'batch_processing_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"报告已保存: {report_path}")

    return summary


def get_pdf_list_from_directory(pdf_dir: str) -> List[Tuple[str, str]]:
    """
    从目录获取PDF列表

    Args:
        pdf_dir: PDF目录

    Returns:
        [(pdf_path, doi), ...]
    """
    pdf_list = []
    pdf_dir_path = Path(pdf_dir)

    for pdf_file in pdf_dir_path.glob('*.pdf'):
        # 从文件名提取DOI（假设文件名格式为: doi_xxx.pdf）
        # 你需要根据实际情况调整
        doi = pdf_file.stem  # 使用文件名作为DOI
        pdf_list.append((str(pdf_file), doi))

    return pdf_list


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='批量处理PDF')
    parser.add_argument('--pdf-dir', type=str, default=PDF_INPUT_DIR,
                        help=f'PDF文件目录（默认：{PDF_INPUT_DIR}）')
    parser.add_argument('--marker-url', type=str, default=MARKER_SERVICE_URL,
                        help=f'Marker服务地址（默认：{MARKER_SERVICE_URL}）')
    parser.add_argument('--max-workers', type=int, default=MAX_WORKERS,
                        help=f'并发数（默认：{MAX_WORKERS}）')
    parser.add_argument('--output-dir', type=str, default=MARKDOWN_OUTPUT_DIR,
                        help=f'输出目录（默认：{MARKDOWN_OUTPUT_DIR}）')

    args = parser.parse_args()

    # 使用命令行参数（覆盖配置文件）
    output_dir = args.output_dir

    # 获取PDF列表
    logger.info(f"扫描PDF目录: {args.pdf_dir}")
    pdf_list = get_pdf_list_from_directory(args.pdf_dir)
    logger.info(f"找到 {len(pdf_list)} 个PDF文件")

    if not pdf_list:
        logger.error("没有找到PDF文件")
        exit(1)

    # 批量处理
    summary = batch_process_pdfs(
        pdf_list,
        marker_service_url=args.marker_url,
        max_workers=args.max_workers
    )

    # 退出码
    exit(0 if summary['failed'] == 0 else 1)
