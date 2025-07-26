#!/usr/bin/env python3
"""
Development utilities for MCP SSH
Usage: python scripts/dev.py [--test|--type-check|--format|--lint|--all]
"""

import subprocess
import sys


def run_command(cmd, description=None):
    """Run a command and return success status"""
    if description:
        print(f"🔄 {description}...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    success = result.returncode == 0
    status = "✅" if success else "❌"
    action = description or " ".join(cmd)
    print(f"{status} {action}")

    return success


def run_tests():
    """Run the test suite with coverage"""
    return run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src/mcp_ssh",
            "--cov-report=term-missing",
            "--cov-report=html",
            "-v",
        ],
        "Running tests with coverage",
    )


def run_type_check():
    """Run mypy type checking"""
    return run_command([sys.executable, "-m", "mypy", "src/"], "Running type checking")


def format_code():
    """Format code with black and isort"""
    black_success = run_command(
        [sys.executable, "-m", "black", "src/", "tests/", "scripts/"],
        "Formatting code with black",
    )

    isort_success = run_command(
        [sys.executable, "-m", "isort", "src/", "tests/", "scripts/"],
        "Sorting imports with isort",
    )

    return black_success and isort_success


def run_lint():
    """Run ruff linting"""
    return run_command(
        [sys.executable, "-m", "ruff", "check", "src/", "tests/", "scripts/"],
        "Running linting with ruff",
    )


def run_all():
    """Run all checks in sequence"""
    print("🚀 Running all development checks...\n")

    success = True

    # Format first
    success &= format_code()
    print()

    # Then lint
    success &= run_lint()
    print()

    # Type check
    success &= run_type_check()
    print()

    # Finally test
    success &= run_tests()
    print()

    if success:
        print("🎉 All checks passed!")
    else:
        print("💥 Some checks failed!")

    return success


def install_dev_deps():
    """Install development dependencies"""
    return run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing development dependencies",
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Development utilities for MCP SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/dev.py --test        # Run tests only
  python scripts/dev.py --format      # Format code only
  python scripts/dev.py --all         # Run everything
  python scripts/dev.py --install     # Install dev dependencies
        """,
    )

    parser.add_argument("--test", action="store_true", help="Run tests with coverage")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument(
        "--install", action="store_true", help="Install dev dependencies"
    )

    args = parser.parse_args()

    # If no args provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0

    success = True

    if args.install:
        success &= install_dev_deps()

    if args.all:
        success = run_all()
    else:
        if args.format:
            success &= format_code()
        if args.lint:
            success &= run_lint()
        if args.type_check:
            success &= run_type_check()
        if args.test:
            success &= run_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
