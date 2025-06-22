#!/usr/bin/env python3
"""Test runner for MedVidDeID pipeline tests."""

import sys
import subprocess
from pathlib import Path

# Change to project root
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def run_test(test_name, description):
    """Run a single test and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, f"tests/{test_name}"
        ], cwd=project_root, check=True)
        print(f"✅ {test_name} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {test_name} - FAILED (exit code: {e.returncode})")
        return False
    except Exception as e:
        print(f"❌ {test_name} - ERROR: {e}")
        return False

def main():
    """Run all basic tests."""
    print("🧪 MedVidDeID Pipeline Test Suite")
    print("Running basic tests (no external dependencies required)")
    
    tests = [
        ("test_artifact_system.py", "Artifact Management System Unit Tests"),
        ("test_pipeline_integration.py", "Pipeline Integration Simulation"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, description in tests:
        if run_test(test_name, description):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print("\nTo test with actual videos, run:")
        print("  python tests/test_video_tracking.py <video_path>")
        print("  python tests/test_video_artifact_only.py <video_path>")
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()