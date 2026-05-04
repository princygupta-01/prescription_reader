#!/usr/bin/env python3
"""
Quick setup verification script for PrescriptionReader
Run this to check if all dependencies are properly installed
"""

import sys
import importlib
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (need 3.11+)")
        return False

def check_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✓ {package_name}")
        return True
    except ImportError:
        print(f"✗ {package_name} (not installed)")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path("backend/.env")
    if not env_path.exists():
        print("✗ backend/.env file not found")
        print("  Copy backend/.env.example to backend/.env and add your GROQ_API_KEY")
        return False
    
    with open(env_path) as f:
        content = f.read()
        
    if "GROQ_API_KEY=" in content and "your_groq_api_key_here" not in content:
        print("✓ backend/.env file configured")
        return True
    else:
        print("✗ backend/.env file missing GROQ_API_KEY")
        print("  Add your Groq API key to backend/.env")
        return False

def check_frontend_deps():
    """Check if frontend dependencies are installed"""
    node_modules = Path("frontend/node_modules")
    if node_modules.exists():
        print("✓ Frontend dependencies installed")
        return True
    else:
        print("✗ Frontend dependencies not installed")
        print("  Run: cd frontend && npm install")
        return False

def main():
    print("PrescriptionReader Setup Verification")
    print("=" * 40)
    
    checks = []
    
    # Python version
    checks.append(check_python_version())
    
    # Backend dependencies
    print("\nBackend Dependencies:")
    backend_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("PIL", "PIL"),
        ("cv2", "cv2"),
        ("groq", "groq"),
        ("reportlab", "reportlab"),
        ("sqlalchemy", "sqlalchemy"),
        ("numpy", "numpy"),
    ]
    
    for package, import_name in backend_deps:
        checks.append(check_package(package, import_name))
    
    # Environment setup
    print("\nConfiguration:")
    checks.append(check_env_file())
    
    # Frontend setup
    print("\nFrontend:")
    checks.append(check_frontend_deps())
    
    # Summary
    print("\n" + "=" * 40)
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✓ All {total} checks passed! Ready to run PrescriptionReader")
        print("\nNext steps:")
        print("1. Start backend: cd backend && uvicorn main:app --reload")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Open http://localhost:3000")
    else:
        print(f"✗ {total - passed} checks failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())