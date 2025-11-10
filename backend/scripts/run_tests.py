#!/usr/bin/env python
"""
Test Runner Script with Coverage Reporting
测试运行脚本与覆盖率报告

Usage:
    # Run all tests with coverage
    python scripts/run_tests.py

    # Run only unit tests
    python scripts/run_tests.py --unit

    # Run only integration tests
    python scripts/run_tests.py --integration

    # Run performance tests
    python scripts/run_tests.py --performance

    # Run with verbose output
    python scripts/run_tests.py --verbose

    # Generate HTML coverage report
    python scripts/run_tests.py --html
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """
    Run pytest with specified options

    Args:
        args: Parsed command-line arguments
    """
    # Base pytest command
    cmd = ["pytest"]

    # Add test selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.performance:
        cmd.extend(["-m", "performance"])
    elif args.contract:
        cmd.extend(["-m", "contract"])

    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add coverage options
    if not args.no_cov:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
        ])

        if args.html:
            cmd.append("--cov-report=html:coverage_html")

    # Add specific test path if provided
    if args.path:
        cmd.append(args.path)

    # Add fail fast option
    if args.failfast:
        cmd.append("-x")

    # Add markers
    if args.markers:
        cmd.extend(["-m", args.markers])

    # Print command
    print(f"Running: {' '.join(cmd)}\n")
    print("=" * 80)

    # Run tests
    try:
        result = subprocess.run(cmd, cwd="backend")
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run tests with coverage reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Test selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests (fast)",
    )
    test_group.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests",
    )
    test_group.add_argument(
        "--performance",
        action="store_true",
        help="Run only performance tests",
    )
    test_group.add_argument(
        "--contract",
        action="store_true",
        help="Run only contract tests",
    )

    # Output options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report",
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage reporting",
    )

    # Test execution options
    parser.add_argument(
        "--failfast",
        "-x",
        action="store_true",
        help="Stop on first test failure",
    )
    parser.add_argument(
        "--markers",
        "-m",
        help="Run tests matching given mark expression",
    )
    parser.add_argument(
        "--path",
        "-p",
        help="Specific test file or directory to run",
    )

    args = parser.parse_args()

    # Run tests
    return_code = run_tests(args)

    # Print coverage report location if HTML was generated
    if args.html and return_code == 0:
        print("\n" + "=" * 80)
        print("HTML coverage report generated:")
        print("  backend/coverage_html/index.html")
        print("=" * 80)

    sys.exit(return_code)


if __name__ == "__main__":
    main()
