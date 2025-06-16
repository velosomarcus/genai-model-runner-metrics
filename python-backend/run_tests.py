"""Test runner script for the Python backend."""

import sys
import subprocess
import os


def run_tests():
    """Run all tests and display results."""
    print("=" * 50)
    print("Running GenAI Python Backend Tests")
    print("=" * 50)
    
    # Change to the python-backend directory
    os.chdir('/home/runner/work/genai-model-runner-metrics/genai-model-runner-metrics/python-backend')
    
    # Set PYTHONPATH
    env = os.environ.copy()
    env['PYTHONPATH'] = '/home/runner/work/genai-model-runner-metrics/genai-model-runner-metrics/python-backend'
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/', 
        '-v', 
        '--tb=short',
        '--disable-warnings'
    ]
    
    try:
        result = subprocess.run(cmd, env=env, check=False, capture_output=False)
        
        print("\n" + "=" * 50)
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
        print("=" * 50)
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)