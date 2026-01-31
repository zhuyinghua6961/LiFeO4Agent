"""
路径配置文件
迁移到 Linux 时只需修改此文件中的路径
"""

# ==================== 路径配置 ====================
# # macOS 路径 (当前)
# PAPERS_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/papers"
# JSON_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/json"
# LFP_HC_JSON_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/lfp_hc_json"
# VECTOR_DATABASE_PATH_STR = "/Users/zhuyinghua/Desktop/code/vector_database_v3"
# COMMUNITY_VECTOR_DB_PATH_STR = "/Users/zhuyinghua/Desktop/agent/main/vector_db"
# DOI_TO_PDF_MAPPING_STR = "/Users/zhuyinghua/Desktop/agent/main/code/backend/doi_to_pdf_mapping.json"
# LOGS_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/logs"
# TRANSLATION_CACHE_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/translation_cache"
# STATIC_DIR_STR = "/Users/zhuyinghua/Desktop/agent/main/static"

# Linux 路径 (迁移时取消注释并注释掉上面的 macOS 路径)
PAPERS_DIR_STR = "/mnt/fast18/zhu/agentCode/papers"
JSON_DIR_STR = "/mnt/fast18/zhu/agentCode/json"
LFP_HC_JSON_DIR_STR = "/mnt/fast18/zhu/agentCode/lfp_hc_json"
VECTOR_DATABASE_PATH_STR = "/mnt/fast18/zhu/LiFeO4Agent/chroma_chunks_v2"
COMMUNITY_VECTOR_DB_PATH_STR = "/mnt/fast18/zhu/agentCode/vector_db"
DOI_TO_PDF_MAPPING_STR = "/mnt/fast18/zhu/LiFeO4Agent/doi_to_pdf_mapping.json"
LOGS_DIR_STR = "/mnt/fast18/zhu/LiFeO4Agent/logs"
TRANSLATION_CACHE_DIR_STR = "/mnt/fast18/zhu/LiFeO4Agent/translation_cache"
STATIC_DIR_STR = "//mnt/fast18/zhu/agentCode/static"
