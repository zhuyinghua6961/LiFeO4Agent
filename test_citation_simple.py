"""
简单测试：验证引用位置增强功能的核心组件
运行: conda run -n py310 python test_citation_simple.py
"""

def test_imports():
    """测试所有组件是否可以正常导入"""
    print("="*80)
    print("🧪 测试组件导入")
    print("="*80)
    
    try:
        print("\n1. 导入CitationLocation...")
        from backend.models.citation_location import CitationLocation
        print("   ✅ CitationLocation导入成功")
        
        print("\n2. 导入ReverseCitationFinder...")
        from backend.agents.reverse_citation_finder import ReverseCitationFinder
        print("   ✅ ReverseCitationFinder导入成功")
        
        print("\n3. 导入EnhancedDOIInserter...")
        from backend.agents.enhanced_doi_inserter import EnhancedDOIInserter
        print("   ✅ EnhancedDOIInserter导入成功")
        
        print("\n4. 导入SemanticExpert...")
        from backend.agents.experts.semantic_expert import SemanticExpert
        print("   ✅ SemanticExpert导入成功")
        
        print("\n" + "="*80)
        print("✅ 所有组件导入成功！")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_citation_location():
    """测试CitationLocation数据模型"""
    print("\n" + "="*80)
    print("🧪 测试CitationLocation数据模型")
    print("="*80)
    
    try:
        from backend.models.citation_location import CitationLocation
        
        # 创建测试实例
        citation = CitationLocation(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="磷酸铁锂的工作电压约为3.4V",
            answer_sentence_index=0,
            source_text="LiFePO4在3.4V附近显示出一个明显的电压平台",
            page=5,
            similarity=0.85,
            chunk_index_in_page=2
        )
        
        print(f"\n✅ 创建CitationLocation成功")
        print(f"   DOI: {citation.doi}")
        print(f"   页码: {citation.page}")
        print(f"   段落: {citation.chunk_index_in_page}")
        print(f"   相似度: {citation.similarity}")
        print(f"   置信度: {citation.confidence}")
        print(f"   显示位置: {citation.get_display_location()}")
        
        # 测试to_dict
        data = citation.to_dict()
        print(f"\n✅ to_dict()成功，包含 {len(data)} 个字段")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_format():
    """测试数据格式兼容性"""
    print("\n" + "="*80)
    print("🧪 测试数据格式兼容性")
    print("="*80)
    
    try:
        from backend.models.citation_location import CitationLocation
        
        citation = CitationLocation(
            doi="10.1016/j.jpowsour.2022.230975",
            answer_sentence="测试句子",
            answer_sentence_index=0,
            source_text="原文片段",
            page=5,
            similarity=0.85,
            chunk_index_in_page=2,
            has_number=True,
            has_unit=True
        )
        
        data = citation.to_dict()
        
        # 检查前端需要的字段
        required_fields = [
            'page', 'chunk_index_in_page', 'similarity', 
            'answer_sentence', 'source_text', 'confidence',
            'has_number', 'has_unit'
        ]
        
        print("\n检查前端需要的字段:")
        all_present = True
        for field in required_fields:
            present = field in data
            status = "✅" if present else "❌"
            print(f"  {status} {field}: {data.get(field)}")
            if not present:
                all_present = False
        
        if all_present:
            print("\n✅ 所有必需字段都存在")
            return True
        else:
            print("\n⚠️ 部分字段缺失")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("🚀 引用位置增强功能 - 简单测试")
    print("="*80)
    
    results = []
    
    # 测试1: 组件导入
    results.append(("组件导入", test_imports()))
    
    # 测试2: CitationLocation
    results.append(("CitationLocation", test_citation_location()))
    
    # 测试3: 数据格式
    results.append(("数据格式兼容性", test_data_format()))
    
    # 总结
    print("\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！功能正常！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
    
    print("="*80)


if __name__ == "__main__":
    main()
