# Test Outputs

此目录包含使用真实文件测试各个模块后生成的 JSON 输出文件。

## 测试文件

标准测试文件：`/mnt/fast18/zhu/LiFeO4Agent/zhang-et-al-2023-ag-plumes-grown-on-cu-for-li-lean-anode-of-high-energy-density-li-metal-batteries_enhanced_clean.md`

## 输出文件

### chunks_test_output.json
- **模块**: ChunkSplitter
- **内容**: 包含所有切分后的 chunks 及其元数据
- **字段**:
  - `metadata`: 测试元数据（源文件、总数、配置等）
  - `chunks`: Chunk 数组，每个包含：
    - `chunk_id`: 唯一标识符
    - `text`: Chunk 文本内容
    - `source`: 源文档标识
    - `chunk_index`: Chunk 索引
    - `start_index`: 在原文中的起始位置
    - `end_index`: 在原文中的结束位置
    - `section`: 章节名称
    - `text_type`: 文本类型（text/table_caption）
    - `doi`: DOI 信息
    - `metadata`: 其他元数据

### sentences_test_output.json (待生成)
- **模块**: SentenceSplitter
- **内容**: 包含所有切分后的句子及其元数据
- **字段**: (待 SentenceSplitter 实现后补充)

## 用途

这些 JSON 文件用于：
1. 验证模块功能的正确性
2. 分析切分效果和质量
3. 作为后续开发和调试的参考
4. 提供给其他模块进行集成测试

## 注意事项

- ⚠️ 这些文件不应被删除
- ⚠️ 每次重新测试会覆盖现有文件
- ⚠️ 文件可能较大（取决于测试文档大小）
