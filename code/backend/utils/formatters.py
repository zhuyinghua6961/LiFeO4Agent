"""
格式化工具
数据格式化、清洗和展示
"""
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class NumberFormatter:
    """数字格式化"""
    
    @staticmethod
    def format_float(value: Optional[float], decimals: int = 4) -> str:
        """
        格式化浮点数
        
        Args:
            value: 原始值
            decimals: 小数位数
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}"
    
    @staticmethod
    def format_percentage(value: Optional[float], decimals: int = 2) -> str:
        """
        格式化百分比
        
        Args:
            value: 原始值
            decimals: 小数位数
            
        Returns:
            格式化后的百分比字符串
        """
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_density(value: Optional[float], unit: str = "g/cm³") -> str:
        """
        格式化密度值
        
        Args:
            value: 原始值
            unit: 单位
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return "N/A"
        return f"{value:.4f} {unit}"
    
    @staticmethod
    def format_capacity(value: Optional[float], unit: str = "mAh/g") -> str:
        """
        格式化容量值
        
        Args:
            value: 原始值
            unit: 单位
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return "N/A"
        return f"{value:.2f} {unit}"
    
    @staticmethod
    def format_range(
        low: Optional[float], 
        high: Optional[float], 
        unit: str = ""
    ) -> str:
        """
        格式化范围值
        
        Args:
            low: 最小值
            high: 最大值
            unit: 单位
            
        Returns:
            格式化后的范围字符串
        """
        if low is None and high is None:
            return "N/A"
        if low is None:
            return f"≤ {high} {unit}"
        if high is None:
            return f"≥ {low} {unit}"
        return f"{low} - {high} {unit}"


class MaterialFormatter:
    """材料数据格式化"""
    
    @staticmethod
    def format_material(material: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化单个材料数据
        
        Args:
            material: 材料原始数据
            
        Returns:
            格式化后的数据
        """
        return {
            "name": material.get("material_name", "Unknown"),
            "doi": material.get("doi", ""),
            "tap_density": NumberFormatter.format_density(
                material.get("tap_density")
            ),
            "compaction_density": NumberFormatter.format_density(
                material.get("compaction_density")
            ),
            "discharge_capacity": NumberFormatter.format_capacity(
                material.get("discharge_capacity")
            ),
            "coulombic_efficiency": NumberFormatter.format_percentage(
                material.get("coulombic_efficiency")
            ),
            "conductivity": NumberFormatter.format_float(
                material.get("conductivity")
            ),
            "particle_size": NumberFormatter.format_float(
                material.get("particle_size"), decimals=1
            ) + " nm" if material.get("particle_size") else "N/A",
            "synthesis_method": material.get("synthesis_method", "N/A"),
            "preparation_method": material.get("preparation_method", "N/A"),
            "carbon_source": material.get("carbon_source", "N/A"),
            "coating_material": material.get("coating_material", "N/A")
        }
    
    @staticmethod
    def format_material_list(materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化材料列表
        
        Args:
            materials: 材料列表
            
        Returns:
            格式化后的列表
        """
        return [MaterialFormatter.format_material(m) for m in materials]
    
    @staticmethod
    def format_material_table(materials: List[Dict[str, Any]]) -> str:
        """
        格式化材料为表格字符串
        
        Args:
            materials: 材料列表
            
        Returns:
            表格字符串
        """
        if not materials:
            return "No materials found"
        
        # 表头
        headers = ["Name", "Tap Density", "Capacity", "Efficiency"]
        rows = []
        
        for m in materials[:10]:  # 限制显示10条
            rows.append([
                m.get("material_name", "N/A")[:30],
                NumberFormatter.format_density(m.get("tap_density")),
                NumberFormatter.format_capacity(m.get("discharge_capacity")),
                NumberFormatter.format_percentage(m.get("coulombic_efficiency"))
            ])
        
        # 计算列宽
        col_widths = [
            max(len(h), max(len(str(row[i])) for row in rows)) 
            for i, h in enumerate(headers)
        ]
        
        # 构建表格
        lines = []
        # 表头
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # 数据行
        for row in rows:
            data_line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))
            lines.append(data_line)
        
        return "\n".join(lines)


class PaperFormatter:
    """文献数据格式化"""
    
    @staticmethod
    def format_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化单个文献数据
        
        Args:
            paper: 文献原始数据
            
        Returns:
            格式化后的数据
        """
        return {
            "id": paper.get("paper_id", "Unknown"),
            "title": paper.get("title", "N/A"),
            "authors": ", ".join(paper.get("authors", [])[:3]) + 
                      ("..." if len(paper.get("authors", [])) > 3 else ""),
            "journal": paper.get("journal", "N/A"),
            "year": paper.get("year", "N/A"),
            "doi": paper.get("doi", ""),
            "abstract_preview": (paper.get("abstract", "")[:200] + "...") 
                               if paper.get("abstract") else "N/A"
        }
    
    @staticmethod
    def format_paper_list(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化文献列表
        
        Args:
            papers: 文献列表
            
        Returns:
            格式化后的列表
        """
        return [PaperFormatter.format_paper(p) for p in papers]


class JSONFormatter:
    """JSON格式化"""
    
    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """
        格式化JSON字符串
        
        Args:
            data: 数据对象
            indent: 缩进空格数
            
        Returns:
            格式化后的JSON字符串
        """
        try:
            return json.dumps(data, ensure_ascii=False, indent=indent)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON格式化失败: {e}")
            return str(data)
    
    @staticmethod
    def minify_json(data: Any) -> str:
        """
        压缩JSON字符串
        
        Args:
            data: 数据对象
            
        Returns:
            压缩后的JSON字符串
        """
        try:
            return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            logger.error(f"JSON压缩失败: {e}")
            return str(data)


class TableFormatter:
    """表格格式化"""
    
    @staticmethod
    def format_table(
        headers: List[str],
        rows: List[List[Any]],
        max_rows: int = 50
    ) -> str:
        """
        格式化表格
        
        Args:
            headers: 表头
            rows: 数据行
            max_rows: 最大显示行数
            
        Returns:
            表格字符串
        """
        if not headers or not rows:
            return "No data"
        
        rows = rows[:max_rows]
        
        # 计算列宽
        col_widths = [
            max(len(str(h)), max(len(str(row[i])) for row in rows) if rows else 0)
            for i, h in enumerate(headers)
        ]
        
        # 构建表格
        lines = []
        
        # 表头
        header_line = "  ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("=" * len(header_line))
        
        # 数据行
        for row in rows:
            data_line = "  ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))
            lines.append(data_line)
        
        # 底部
        lines.append("=" * len(header_line))
        lines.append(f"Total: {len(rows)} rows")
        
        return "\n".join(lines)


class ResponseFormatter:
    """API响应格式化"""
    
    @staticmethod
    def success(
        data: Any,
        message: str = "Success",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        格式化成功响应
        
        Args:
            data: 响应数据
            message: 消息
            metadata: 元数据
            
        Returns:
            响应字典
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            response["metadata"] = metadata
        return response
    
    @staticmethod
    def error(
        message: str,
        code: str = "ERROR",
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        格式化错误响应
        
        Args:
            message: 错误消息
            code: 错误码
            details: 详细信息
            
        Returns:
            响应字典
        """
        response = {
            "success": False,
            "error": {
                "message": message,
                "code": code
            },
            "timestamp": datetime.now().isoformat()
        }
        if details:
            response["error"]["details"] = details
        return response
    
    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        page_size: int,
        total: int
    ) -> Dict[str, Any]:
        """
        格式化分页响应
        
        Args:
            data: 数据列表
            page: 当前页
            page_size: 每页大小
            total: 总数
            
        Returns:
            响应字典
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "timestamp": datetime.now().isoformat()
        }


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_duration(seconds: float) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时长字符串
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    else:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)}m {secs:.2f}s"
