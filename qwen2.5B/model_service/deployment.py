"""
模型部署服务

提供模型下载、vLLM 服务启动、健康检查和监控功能。
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str
    model_path: str
    device: str = "cuda"
    max_batch_size: int = 32
    max_seq_length: int = 4096
    port: int = 8003
    framework: str = "vllm"
    hf_mirror: str = "https://hf-mirror.com"


@dataclass
class HealthStatus:
    """健康状态"""
    is_healthy: bool
    message: str
    timestamp: float


@dataclass
class ServiceMetrics:
    """服务指标"""
    uptime: float
    total_requests: int
    active_requests: int
    average_latency: float
    error_rate: float


class ModelDeploymentService:
    """模型部署服务"""
    
    def __init__(self, config: ModelConfig):
        """
        初始化模型部署服务
        
        Args:
            config: 模型配置
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        
    def download_model(self, cache_dir: Optional[str] = None) -> bool:
        """
        从 Hugging Face 下载模型
        
        Args:
            cache_dir: 模型缓存目录，默认使用配置中的路径
            
        Returns:
            bool: 下载是否成功
        """
        try:
            # 设置 Hugging Face 镜像
            os.environ['HF_ENDPOINT'] = self.config.hf_mirror
            logger.info(f"设置 HF_ENDPOINT={self.config.hf_mirror}")
            
            # 确定缓存目录
            if cache_dir is None:
                cache_dir = self.config.model_path
            
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"开始下载模型: {self.config.model_name}")
            logger.info(f"缓存目录: {cache_dir}")
            
            # 使用 transformers 下载模型
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                
                # 下载 tokenizer
                logger.info("下载 tokenizer...")
                tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_name,
                    cache_dir=cache_dir,
                    trust_remote_code=True
                )
                
                # 下载模型
                logger.info("下载模型权重...")
                model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_name,
                    cache_dir=cache_dir,
                    trust_remote_code=True,
                    device_map=None  # 不加载到设备，只下载
                )
                
                logger.info(f"模型下载成功: {self.config.model_name}")
                return True
                
            except ImportError:
                logger.error("transformers 库未安装，请先安装依赖")
                return False
            except Exception as e:
                logger.error(f"模型下载失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"下载模型时发生错误: {e}")
            return False
    
    def start_service(self) -> bool:
        """
        启动 vLLM 模型服务
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if self.config.framework != "vllm":
                logger.error(f"不支持的框架: {self.config.framework}")
                return False
            
            logger.info("启动 vLLM 服务...")
            logger.info(f"模型: {self.config.model_name}")
            logger.info(f"端口: {self.config.port}")
            logger.info(f"设备: {self.config.device}")
            
            # 构建 vLLM 启动命令
            cmd = [
                sys.executable, "-m", "vllm.entrypoints.openai.api_server",
                "--model", self.config.model_name,
                "--port", str(self.config.port),
                "--max-model-len", str(self.config.max_seq_length),
            ]
            
            # 添加 GPU 相关参数
            if self.config.device == "cuda":
                cmd.extend(["--gpu-memory-utilization", "0.9"])
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.start_time = time.time()
            
            # 等待服务启动
            logger.info("等待服务启动...")
            max_wait = 60  # 最多等待 60 秒
            wait_interval = 2  # 每 2 秒检查一次
            
            for i in range(max_wait // wait_interval):
                time.sleep(wait_interval)
                
                # 检查进程是否还在运行
                if self.process.poll() is not None:
                    logger.error("vLLM 进程意外退出")
                    return False
                
                # 检查服务是否可用
                health = self.health_check()
                if health.is_healthy:
                    logger.info(f"vLLM 服务启动成功 (耗时 {(i+1)*wait_interval} 秒)")
                    return True
            
            logger.error(f"服务启动超时 ({max_wait} 秒)")
            return False
            
        except Exception as e:
            logger.error(f"启动服务时发生错误: {e}")
            return False
    
    def stop_service(self) -> bool:
        """
        停止模型服务
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if self.process is None:
                logger.warning("服务未运行")
                return True
            
            logger.info("停止 vLLM 服务...")
            self.process.terminate()
            
            # 等待进程结束
            try:
                self.process.wait(timeout=10)
                logger.info("服务已停止")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("进程未响应，强制终止")
                self.process.kill()
                self.process.wait()
                return True
                
        except Exception as e:
            logger.error(f"停止服务时发生错误: {e}")
            return False
    
    def health_check(self) -> HealthStatus:
        """
        健康检查
        
        Returns:
            HealthStatus: 健康状态
        """
        try:
            url = f"http://localhost:{self.config.port}/v1/models"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return HealthStatus(
                    is_healthy=True,
                    message="服务正常运行",
                    timestamp=time.time()
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message=f"服务返回错误状态码: {response.status_code}",
                    timestamp=time.time()
                )
                
        except requests.exceptions.ConnectionError:
            return HealthStatus(
                is_healthy=False,
                message="无法连接到服务",
                timestamp=time.time()
            )
        except requests.exceptions.Timeout:
            return HealthStatus(
                is_healthy=False,
                message="连接超时",
                timestamp=time.time()
            )
        except Exception as e:
            return HealthStatus(
                is_healthy=False,
                message=f"健康检查失败: {e}",
                timestamp=time.time()
            )
    
    def get_metrics(self) -> ServiceMetrics:
        """
        获取服务指标
        
        Returns:
            ServiceMetrics: 服务指标
        """
        try:
            # 计算运行时间
            uptime = 0.0
            if self.start_time is not None:
                uptime = time.time() - self.start_time
            
            # 尝试从 vLLM 获取指标
            # 注意: vLLM 可能不提供详细的指标 API，这里返回基本信息
            return ServiceMetrics(
                uptime=uptime,
                total_requests=0,  # vLLM 不直接提供
                active_requests=0,  # vLLM 不直接提供
                average_latency=0.0,  # vLLM 不直接提供
                error_rate=0.0  # vLLM 不直接提供
            )
            
        except Exception as e:
            logger.error(f"获取指标时发生错误: {e}")
            return ServiceMetrics(
                uptime=0.0,
                total_requests=0,
                active_requests=0,
                average_latency=0.0,
                error_rate=0.0
            )
    
    def is_running(self) -> bool:
        """
        检查服务是否正在运行
        
        Returns:
            bool: 服务是否运行
        """
        if self.process is None:
            return False
        
        # 检查进程是否存活
        if self.process.poll() is not None:
            return False
        
        # 检查健康状态
        health = self.health_check()
        return health.is_healthy


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="模型部署服务")
    parser.add_argument("--action", choices=["download", "start", "stop", "status"],
                       required=True, help="操作: download/start/stop/status")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-1.5B-Instruct",
                       help="模型名称")
    parser.add_argument("--model-path", default="./models/qwen2.5-1.5b-instruct",
                       help="模型路径")
    parser.add_argument("--port", type=int, default=8003, help="服务端口")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda",
                       help="设备类型")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建配置
    config = ModelConfig(
        model_name=args.model_name,
        model_path=args.model_path,
        port=args.port,
        device=args.device
    )
    
    # 创建服务
    service = ModelDeploymentService(config)
    
    # 执行操作
    if args.action == "download":
        success = service.download_model()
        sys.exit(0 if success else 1)
    
    elif args.action == "start":
        success = service.start_service()
        if success:
            print(f"服务已启动，端口: {args.port}")
            print("按 Ctrl+C 停止服务")
            try:
                # 保持运行
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n停止服务...")
                service.stop_service()
        sys.exit(0 if success else 1)
    
    elif args.action == "stop":
        success = service.stop_service()
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        health = service.health_check()
        print(f"健康状态: {'正常' if health.is_healthy else '异常'}")
        print(f"消息: {health.message}")
        
        if health.is_healthy:
            metrics = service.get_metrics()
            print(f"运行时间: {metrics.uptime:.2f} 秒")
        
        sys.exit(0 if health.is_healthy else 1)


if __name__ == "__main__":
    main()
