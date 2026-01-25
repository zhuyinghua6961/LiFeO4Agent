"""
Validation script to verify the rebuild_vector_db setup.
"""

import os
import sys
import yaml


def validate_environment():
    """Validate that we're running in the correct environment."""
    print("=" * 60)
    print("Validating Environment Setup")
    print("=" * 60)
    
    # Check Python version
    print(f"\n✓ Python version: {sys.version.split()[0]}")
    
    # Check required packages
    required_packages = [
        'yaml',
        'tqdm',
        'requests',
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ Package '{package}' is available")
        except ImportError:
            print(f"✗ Package '{package}' is MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠ Warning: Missing packages: {', '.join(missing_packages)}")
        print("Install them with: conda run -n agent pip install -r rebuild_vector_db/requirements.txt")
    
    return len(missing_packages) == 0


def validate_directories():
    """Validate that required directories exist."""
    print("\n" + "=" * 60)
    print("Validating Directory Structure")
    print("=" * 60)
    
    required_dirs = [
        'rebuild_vector_db',
        'config',
        'logs',
        'reports',
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✓ Directory '{dir_path}' exists")
        else:
            print(f"✗ Directory '{dir_path}' is MISSING")
            all_exist = False
    
    return all_exist


def validate_config():
    """Validate that configuration file exists and is valid."""
    print("\n" + "=" * 60)
    print("Validating Configuration")
    print("=" * 60)
    
    config_path = 'config/rebuild_config.yaml'
    
    if not os.path.exists(config_path):
        print(f"✗ Configuration file '{config_path}' is MISSING")
        return False
    
    print(f"✓ Configuration file '{config_path}' exists")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"✓ Configuration file is valid YAML")
        
        # Check required keys
        required_keys = [
            'chunk_size',
            'chunk_overlap',
            'bge_api_url',
            'chunk_db_path',
            'sentence_db_path',
        ]
        
        missing_keys = []
        for key in required_keys:
            if key in config:
                value = config[key]
                # Validate BGE API URL
                if key == 'bge_api_url' and 'localhost:8001/v1/embeddings' not in value:
                    print(f"  ⚠ Config key '{key}': {value}")
                    print(f"    Warning: Expected localhost:8001/v1/embeddings")
                else:
                    print(f"  ✓ Config key '{key}': {value}")
            else:
                print(f"  ✗ Config key '{key}' is MISSING")
                missing_keys.append(key)
        
        return len(missing_keys) == 0
        
    except Exception as e:
        print(f"✗ Error reading configuration: {e}")
        return False


def validate_bge_api():
    """Validate that BGE API is accessible."""
    print("\n" + "=" * 60)
    print("Validating BGE API Connection")
    print("=" * 60)
    
    try:
        import requests
        
        # Load config to get API URL
        config_path = 'config/rebuild_config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        api_url = config.get('bge_api_url', 'http://localhost:8001/v1/embeddings')
        print(f"Testing BGE API at: {api_url}")
        
        # Test with a simple request
        response = requests.post(
            api_url,
            json={"input": ["测试文本"]},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            embedding = data["data"][0]["embedding"]
            print(f"✓ BGE API is accessible")
            print(f"✓ Embedding dimension: {len(embedding)}")
            return True
        else:
            print(f"✗ BGE API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to BGE API")
        print(f"  Make sure the BGE service is running on port 8001")
        return False
    except Exception as e:
        print(f"✗ Error testing BGE API: {e}")
        return False


def validate_modules():
    """Validate that all modules can be imported."""
    print("\n" + "=" * 60)
    print("Validating Modules")
    print("=" * 60)
    
    modules = [
        'rebuild_vector_db',
        'rebuild_vector_db.chunk_splitter',
        'rebuild_vector_db.sentence_splitter',
        'rebuild_vector_db.bge_embedder',
        'rebuild_vector_db.chromadb_manager',
        'rebuild_vector_db.pipeline',
    ]
    
    all_importable = True
    for module in modules:
        try:
            __import__(module)
            print(f"✓ Module '{module}' can be imported")
        except Exception as e:
            print(f"✗ Module '{module}' import failed: {e}")
            all_importable = False
    
    return all_importable


def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("REBUILD VECTOR DATABASE - SETUP VALIDATION")
    print("=" * 60)
    
    results = {
        'Environment': validate_environment(),
        'Directories': validate_directories(),
        'Configuration': validate_config(),
        'BGE API': validate_bge_api(),
        'Modules': validate_modules(),
    }
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{check}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All validation checks passed!")
        print("The rebuild_vector_db system is ready to use.")
        return 0
    else:
        print("\n✗ Some validation checks failed.")
        print("Please fix the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
