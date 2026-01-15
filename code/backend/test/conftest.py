"""
Pytest配置文件
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

# 确保 backend 目录在路径中
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
    
# 也添加项目根目录
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def backend_path(project_root):
    """后端目录"""
    return project_root / "backend"


@pytest.fixture(scope="session")
def txt_path(backend_path):
    """提示词目录"""
    return backend_path / "txt"


@pytest.fixture
def sample_material_data():
    """示例材料数据"""
    return {
        "material_name": "LiFePO4",
        "doi": "10.1234/test",
        "tap_density": 2.5,
        "compaction_density": 2.8,
        "discharge_capacity": 160.0,
        "coulombic_efficiency": 99.0,
        "synthesis_method": "固相法",
        "particle_size": 500.0,
        "conductivity": 1e-9
    }


@pytest.fixture
def sample_paper_data():
    """示例文献数据"""
    return {
        "paper_id": "test_001",
        "title": "Test Paper on LiFePO4",
        "authors": ["Author1", "Author2", "Author3"],
        "journal": "Journal of Electrochemical Society",
        "year": 2024,
        "doi": "10.1234/test.001",
        "abstract": "This is a test abstract."
    }
