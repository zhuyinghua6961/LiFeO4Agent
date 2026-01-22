"""
测试CitationLocation数据模型
运行: conda run -n py310 pytest backend/test/test_citation_location.py -v
"""
import pytest
from backend.models.citation_location import CitationLocation


class TestCitationLocation:
    """测试CitationLocation数据模型"""
    
    def test_basic_creation(self):
        """测试基本创建"""
        location = CitationLocation(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="磷酸铁锂的工作电压约为3.4V",
            answer_sentence_index=0,
            source_text="LiFePO4在3.4V附近显示出一个明显的电压平台",
            page=5,
            similarity=0.85
        )
        
        assert location.doi == "10.1016/j.jpowsour.2022.230975"
        assert location.page == 5
        assert location.similarity == 0.85
        assert location.confidence == "high"  # 自动设置
    
    def test_similarity_validation(self):
        """测试相似度验证"""
        # 有效范围
        location = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=1,
            similarity=0.5
        )
        assert location.similarity == 0.5
        
        # 无效范围 - 太大
        with pytest.raises(ValueError, match="相似度必须在"):
            CitationLocation(
                doi="test",
                answer_sentence="test",
                answer_sentence_index=0,
                source_text="test",
                page=1,
                similarity=1.5
            )
        
        # 无效范围 - 负数
        with pytest.raises(ValueError, match="相似度必须在"):
            CitationLocation(
                doi="test",
                answer_sentence="test",
                answer_sentence_index=0,
                source_text="test",
                page=1,
                similarity=-0.1
            )
    
    def test_page_validation(self):
        """测试页码验证"""
        # 有效页码
        location = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=1,
            similarity=0.5
        )
        assert location.page == 1
        
        # 无效页码
        with pytest.raises(ValueError, match="页码必须为正整数"):
            CitationLocation(
                doi="test",
                answer_sentence="test",
                answer_sentence_index=0,
                source_text="test",
                page=-1,
                similarity=0.5
            )
    
    def test_confidence_auto_setting(self):
        """测试置信度自动设置"""
        # 高相似度 -> high
        location_high = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=1,
            similarity=0.8
        )
        assert location_high.confidence == "high"
        
        # 中等相似度 -> medium
        location_medium = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=1,
            similarity=0.6
        )
        assert location_medium.confidence == "medium"
        
        # 低相似度 -> low
        location_low = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=1,
            similarity=0.3
        )
        assert location_low.confidence == "low"
    
    def test_from_sentence_db(self):
        """测试从句子级数据库创建"""
        sentence_metadata = {
            "sentence_index": 42,
            "has_number": True,
            "has_unit": True,
            "word_count": 50
        }
        
        location = CitationLocation.from_sentence_db(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="磷酸铁锂的工作电压约为3.4V",
            answer_sentence_index=0,
            sentence_text="LiFePO4在3.4V附近显示出一个明显的电压平台",
            sentence_metadata=sentence_metadata,
            similarity=0.85,
            page=5,
            keywords=["3.4V", "电压平台"]
        )
        
        assert location.sentence_index == 42
        assert location.has_number is True
        assert location.has_unit is True
        assert location.keywords == ["3.4V", "电压平台"]
    
    def test_from_paragraph_db(self):
        """测试从段落级数据库创建"""
        paragraph_metadata = {
            "page": 5,
            "chunk_index_in_page": 1,
            "chunk_index_global": 10,
            "doi": "10.1016/j.jpowsour.2022.230975"
        }
        
        location = CitationLocation.from_paragraph_db(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="磷酸铁锂的工作电压约为3.4V",
            answer_sentence_index=0,
            paragraph_text="LiFePO4在3.4V附近显示出一个明显的电压平台。" * 20,  # 长文本
            paragraph_metadata=paragraph_metadata,
            similarity=0.75,
            keywords=["3.4V"]
        )
        
        assert location.page == 5
        assert location.chunk_index_in_page == 1
        assert location.chunk_index_global == 10
        assert len(location.source_text) <= 500  # 限制长度
    
    def test_to_dict(self):
        """测试转换为字典"""
        location = CitationLocation(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="磷酸铁锂的工作电压约为3.4V",
            answer_sentence_index=0,
            source_text="LiFePO4在3.4V附近显示出一个明显的电压平台",
            page=5,
            similarity=0.85432,
            keywords=["3.4V", "电压平台"],
            sentence_index=42,
            has_number=True,
            has_unit=True,
            chunk_index_in_page=1
        )
        
        result = location.to_dict()
        
        assert result["doi"] == "10.1016/j.jpowsour.2022.230975"
        assert result["page"] == 5
        assert result["similarity"] == 0.8543  # 四舍五入到4位
        assert result["keywords"] == ["3.4V", "电压平台"]
        assert result["sentence_index"] == 42
        assert result["has_number"] is True
        assert result["has_unit"] is True
        assert result["chunk_index_in_page"] == 1
    
    def test_get_display_location(self):
        """测试获取显示位置"""
        # 有chunk_index_in_page
        location_with_chunk = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=5,
            similarity=0.8,
            chunk_index_in_page=1  # 第2段（从0开始）
        )
        assert location_with_chunk.get_display_location() == "第5页第2段"
        
        # 没有chunk_index_in_page
        location_without_chunk = CitationLocation(
            doi="test",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=5,
            similarity=0.8
        )
        assert location_without_chunk.get_display_location() == "第5页"
    
    def test_repr(self):
        """测试字符串表示"""
        location = CitationLocation(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="test",
            answer_sentence_index=0,
            source_text="test",
            page=5,
            similarity=0.85
        )
        
        repr_str = repr(location)
        assert "10.1016/j.jpowsour.2022.230975" in repr_str
        assert "page=5" in repr_str
        assert "0.850" in repr_str
        assert "high" in repr_str
