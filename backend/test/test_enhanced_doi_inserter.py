"""
测试EnhancedDOIInserter类
运行环境: conda run -n py310 pytest backend/test/test_enhanced_doi_inserter.py
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.agents.enhanced_doi_inserter import EnhancedDOIInserter
from backend.models.citation_location import CitationLocation


@pytest.fixture
def mock_collections():
    """创建模拟的数据库collections"""
    sentence_collection = Mock()
    paragraph_collection = Mock()
    return sentence_collection, paragraph_collection


@pytest.fixture
def inserter(mock_collections):
    """创建EnhancedDOIInserter实例"""
    sentence_collection, paragraph_collection = mock_collections
    bge_api_url = "http://localhost:8000/embeddings"
    
    return EnhancedDOIInserter(
        sentence_collection=sentence_collection,
        paragraph_collection=paragraph_collection,
        bge_api_url=bge_api_url
    )


def test_init(inserter):
    """测试初始化"""
    assert inserter.sentence_collection is not None
    assert inserter.paragraph_collection is not None
    assert inserter.bge_api_url == "http://localhost:8000/embeddings"
    assert inserter.reverse_finder is not None


def test_split_sentences(inserter):
    """测试句子拆分"""
    text = "这是第一句。这是第二句？这是第三句！"
    sentences = inserter._split_sentences(text)
    
    assert len(sentences) == 3
    assert sentences[0] == "这是第一句。"
    assert sentences[1] == "这是第二句？"
    assert sentences[2] == "这是第三句！"


def test_split_sentences_with_newlines(inserter):
    """测试包含换行符的句子拆分"""
    text = "第一句。\n第二句。\n第三句。"
    sentences = inserter._split_sentences(text)
    
    assert len(sentences) == 3


def test_split_sentences_empty(inserter):
    """测试空文本拆分"""
    text = ""
    sentences = inserter._split_sentences(text)
    
    assert len(sentences) == 0


def test_extract_candidate_dois(inserter):
    """测试提取候选DOI"""
    documents = [
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.230975"}},
        {"metadata": {"DOI": "10.1016/j.jelechem.2023.117275"}},
        {"metadata": {"doi": "N/A"}},  # 应该被过滤
        {"metadata": {"doi": "unknown"}},  # 应该被过滤
        {"metadata": {}},  # 没有DOI
    ]
    
    dois = inserter._extract_candidate_dois(documents)
    
    assert len(dois) == 2
    assert "10.1016/j.jpowsour.2022.230975" in dois
    assert "10.1016/j.jelechem.2023.117275" in dois


def test_get_page_for_doi(inserter, mock_collections):
    """测试获取页码"""
    _, paragraph_collection = mock_collections
    
    # 模拟数据库返回
    paragraph_collection.get.return_value = {
        'metadatas': [{'page': 5}]
    }
    
    page = inserter._get_page_for_doi("10.1016/j.jpowsour.2022.230975")
    
    assert page == 5
    paragraph_collection.get.assert_called_once()


def test_get_page_for_doi_not_found(inserter, mock_collections):
    """测试DOI不存在时获取页码"""
    _, paragraph_collection = mock_collections
    
    # 模拟数据库返回空结果
    paragraph_collection.get.return_value = {
        'metadatas': []
    }
    
    page = inserter._get_page_for_doi("10.1016/j.nonexistent")
    
    assert page == 0


def test_merge_locations_no_overlap(inserter):
    """测试合并引用位置（无重叠）"""
    step1_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="句子1",
                answer_sentence_index=0,
                source_text="原文1",
                page=1,
                similarity=0.8
            )
        ]
    }
    
    step2_locations = {
        "doi2": [
            CitationLocation(
                doi="doi2",
                answer_sentence="句子2",
                answer_sentence_index=1,
                source_text="原文2",
                page=2,
                similarity=0.7
            )
        ]
    }
    
    merged = inserter._merge_locations(step1_locations, step2_locations)
    
    assert len(merged) == 2
    assert "doi1" in merged
    assert "doi2" in merged
    assert len(merged["doi1"]) == 1
    assert len(merged["doi2"]) == 1


def test_merge_locations_with_overlap(inserter):
    """测试合并引用位置（有重叠）"""
    # 同一个DOI在两个步骤中都找到了
    step1_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="句子1",
                answer_sentence_index=0,
                source_text="原文1",
                page=1,
                similarity=0.8
            )
        ]
    }
    
    step2_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="句子2",
                answer_sentence_index=1,
                source_text="原文2",
                page=2,
                similarity=0.7
            )
        ]
    }
    
    merged = inserter._merge_locations(step1_locations, step2_locations)
    
    assert len(merged) == 1
    assert "doi1" in merged
    assert len(merged["doi1"]) == 2  # 两个不同的句子


def test_merge_locations_deduplication(inserter):
    """测试合并引用位置（去重）"""
    # 同一个DOI的同一个句子在两个步骤中都找到了
    step1_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="句子1",
                answer_sentence_index=0,
                source_text="原文1",
                page=1,
                similarity=0.8
            )
        ]
    }
    
    step2_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="句子1",
                answer_sentence_index=0,  # 相同的句子索引
                source_text="原文2",
                page=2,
                similarity=0.9  # 更高的相似度
            )
        ]
    }
    
    merged = inserter._merge_locations(step1_locations, step2_locations)
    
    assert len(merged) == 1
    assert "doi1" in merged
    assert len(merged["doi1"]) == 1  # 去重后只有1个
    assert merged["doi1"][0].similarity == 0.9  # 保留相似度更高的


def test_insert_dois_to_answer(inserter):
    """测试插入DOI到答案"""
    answer_sentences = [
        "这是第一句。",
        "这是第二句。",
        "这是第三句。"
    ]
    
    doi_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="这是第一句。",
                answer_sentence_index=0,
                source_text="原文1",
                page=1,
                similarity=0.8
            )
        ],
        "doi2": [
            CitationLocation(
                doi="doi2",
                answer_sentence="这是第三句。",
                answer_sentence_index=2,
                source_text="原文2",
                page=2,
                similarity=0.7
            )
        ]
    }
    
    answer_with_dois = inserter._insert_dois_to_answer(answer_sentences, doi_locations)
    
    assert "(doi=doi1)" in answer_with_dois
    assert "(doi=doi2)" in answer_with_dois
    assert "这是第二句。" in answer_with_dois  # 第二句没有DOI


def test_insert_dois_to_answer_multiple_dois_same_sentence(inserter):
    """测试同一句子有多个DOI时只插入相似度最高的"""
    answer_sentences = ["这是一句话。"]
    
    doi_locations = {
        "doi1": [
            CitationLocation(
                doi="doi1",
                answer_sentence="这是一句话。",
                answer_sentence_index=0,
                source_text="原文1",
                page=1,
                similarity=0.7
            )
        ],
        "doi2": [
            CitationLocation(
                doi="doi2",
                answer_sentence="这是一句话。",
                answer_sentence_index=0,
                source_text="原文2",
                page=2,
                similarity=0.9  # 更高的相似度
            )
        ]
    }
    
    answer_with_dois = inserter._insert_dois_to_answer(answer_sentences, doi_locations)
    
    # 应该只插入doi2（相似度更高）
    assert "(doi=doi2)" in answer_with_dois
    assert "(doi=doi1)" not in answer_with_dois


@patch('backend.agents.enhanced_doi_inserter.requests.post')
def test_insert_dois_with_full_coverage_empty_answer(mock_post, inserter):
    """测试空答案的处理"""
    answer = ""
    documents = []
    reference_dois = []
    
    result_answer, result_locations = inserter.insert_dois_with_full_coverage(
        answer=answer,
        documents=documents,
        reference_dois=reference_dois
    )
    
    assert result_answer == ""
    assert result_locations == {}


@patch('backend.agents.enhanced_doi_inserter.requests.post')
def test_find_dois_for_sentences_no_candidates(mock_post, inserter):
    """测试没有候选DOI时的处理"""
    answer_sentences = ["这是一句话。"]
    documents = []  # 没有文档
    
    locations = inserter._find_dois_for_sentences(
        answer_sentences=answer_sentences,
        documents=documents,
        similarity_threshold=0.5
    )
    
    assert locations == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
