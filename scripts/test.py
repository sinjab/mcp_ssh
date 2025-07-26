#!/usr/bin/env python3
"""
Simple test runner for quick development testing
Usage: python scripts/test.py [test_name_pattern]
"""

import subprocess
import sys


def main():
    """Run tests with optional pattern matching"""
    args = [sys.executable, "-m", "pytest", "-v"]

    # Add test pattern if provided
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        args.extend(["-k", pattern])

    # Add coverage for detailed runs
    if "--cov" not in sys.argv:
        args.extend(["--cov=src/mcp_ssh", "--cov-report=term-missing"])

    # Run the tests
    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
