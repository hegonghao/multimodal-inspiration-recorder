#!/usr/bin/env python3
"""
Deployment Readiness Checklist Script
Validates production readiness before deployment
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_section(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print("-" * 70)


def print_check(name: str, passed: bool, message: str = ""):
    """Print check result"""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if message:
        prefix = "  " if passed else f"  {Colors.RED}"
        suffix = "" if passed else Colors.END
        print(f"{prefix}{message}{suffix}")


def check_environment_variables() -> Tuple[bool, List[str]]:
    """Check required environment variables"""
    required_vars = [
        "SECRET_KEY",
    ]

    optional_vars = [
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
        "SENTRY_DSN",
    ]

    issues = []
    warnings = []

    # Check required
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")

    # Check optional
    for var in optional_vars:
        if not os.getenv(var):
            warnings.append(f"Optional environment variable not set: {var}")

    # Check SECRET_KEY length
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key and len(secret_key) < 32:
        issues.append("SECRET_KEY must be at least 32 characters")

    return len(issues) == 0, issues + [f"⚠️ {w}" for w in warnings]


def check_configuration_files() -> Tuple[bool, List[str]]:
    """Check configuration files exist"""
    backend_root = Path(__file__).parent.parent
    required_files = [
        ".env.example",
        "requirements.txt",
        "alembic.ini",
    ]

    optional_files = [
        ".env.production",
        "docker-compose.yml",
        "Dockerfile",
    ]

    issues = []
    warnings = []

    # Check required files
    for file in required_files:
        file_path = backend_root / file
        if not file_path.exists():
            issues.append(f"Missing required file: {file}")

    # Check optional files
    for file in optional_files:
        file_path = backend_root / file
        if not file_path.exists():
            warnings.append(f"Optional file not found: {file}")

    return len(issues) == 0, issues + [f"⚠️ {w}" for w in warnings]


def check_database_migrations() -> Tuple[bool, List[str]]:
    """Check database migrations are ready"""
    backend_root = Path(__file__).parent.parent
    migrations_dir = backend_root / "alembic" / "versions"

    issues = []

    if not migrations_dir.exists():
        issues.append("Migrations directory not found: alembic/versions")
        return False, issues

    migration_files = list(migrations_dir.glob("*.py"))
    if not migration_files:
        issues.append("No migration files found in alembic/versions")
        return False, issues

    return True, [f"Found {len(migration_files)} migration files"]


def check_tests() -> Tuple[bool, List[str]]:
    """Check if tests exist and can be run"""
    backend_root = Path(__file__).parent.parent
    tests_dir = backend_root / "tests"

    issues = []
    warnings = []

    if not tests_dir.exists():
        issues.append("Tests directory not found: tests/")
        return False, issues

    # Count test files
    test_files = list(tests_dir.rglob("test_*.py"))
    if not test_files:
        warnings.append("No test files found in tests/")

    # Check for pytest configuration
    pytest_ini = backend_root / "pytest.ini"
    if not pytest_ini.exists():
        warnings.append("pytest.ini configuration not found")

    messages = [f"Found {len(test_files)} test files"]
    if warnings:
        messages.extend([f"⚠️ {w}" for w in warnings])

    return len(issues) == 0, messages


def check_security_configuration() -> Tuple[bool, List[str]]:
    """Check security settings"""
    issues = []
    warnings = []

    # Check DEBUG mode
    debug_mode = os.getenv("DEBUG", "False").lower()
    if debug_mode in ["true", "1", "yes"]:
        issues.append("DEBUG mode is enabled - MUST be False in production")

    # Check CORS settings
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if "*" in cors_origins:
        warnings.append("CORS_ORIGINS includes '*' - restrict to specific domains")

    # Check HTTPS enforcement
    # Note: This should be checked at deployment/infrastructure level
    warnings.append("Verify HTTPS is enforced at load balancer/ingress level")

    return len(issues) == 0, issues + [f"⚠️ {w}" for w in warnings]


def check_logging_configuration() -> Tuple[bool, List[str]]:
    """Check logging is properly configured"""
    backend_root = Path(__file__).parent.parent
    issues = []
    warnings = []

    # Check logs directory
    logs_dir = backend_root / "logs"
    if not logs_dir.exists():
        warnings.append("Logs directory does not exist - will be created at runtime")

    # Check log level
    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level == "DEBUG":
        warnings.append("LOG_LEVEL is DEBUG - consider INFO or WARNING for production")

    return len(issues) == 0, issues + [f"⚠️ {w}" for w in warnings]


def check_dependency_versions() -> Tuple[bool, List[str]]:
    """Check dependencies are pinned"""
    backend_root = Path(__file__).parent.parent
    requirements_file = backend_root / "requirements.txt"

    issues = []
    warnings = []

    if not requirements_file.exists():
        issues.append("requirements.txt not found")
        return False, issues

    with open(requirements_file, "r") as f:
        lines = f.readlines()

    unpinned = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            if ">=" in line or "~=" in line or not any(op in line for op in ["==", "="]):
                unpinned.append(line.split()[0])

    if unpinned:
        warnings.append(
            f"Found {len(unpinned)} unpinned dependencies - consider pinning for production"
        )

    return True, [f"Checked {len(lines)} lines in requirements.txt"] + [
        f"⚠️ {w}" for w in warnings
    ]


def run_all_checks() -> Dict[str, Tuple[bool, List[str]]]:
    """Run all deployment checks"""
    checks = {
        "Environment Variables": check_environment_variables(),
        "Configuration Files": check_configuration_files(),
        "Database Migrations": check_database_migrations(),
        "Tests": check_tests(),
        "Security Configuration": check_security_configuration(),
        "Logging Configuration": check_logging_configuration(),
        "Dependency Versions": check_dependency_versions(),
    }

    return checks


def main():
    """Main deployment checklist script"""
    print_header("🚀 PRODUCTION DEPLOYMENT READINESS CHECKLIST")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'unknown')}")

    # Run all checks
    results = run_all_checks()

    # Print results
    for section, (passed, messages) in results.items():
        print_section(f"📋 {section}")
        print_check(section, passed, "\n  ".join(messages) if messages else "")

    # Summary
    print_header("📊 SUMMARY")

    total_checks = len(results)
    passed_checks = sum(1 for passed, _ in results.values() if passed)
    failed_checks = total_checks - passed_checks

    print(f"Total Checks: {total_checks}")
    print(f"{Colors.GREEN}Passed: {passed_checks}{Colors.END}")

    if failed_checks > 0:
        print(f"{Colors.RED}Failed: {failed_checks}{Colors.END}")

    # Overall status
    all_passed = failed_checks == 0

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ READY FOR DEPLOYMENT{Colors.END}\n")
        print("All critical checks passed. Review warnings before deploying.")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ NOT READY FOR DEPLOYMENT{Colors.END}\n")
        print("Please fix the failed checks before deploying to production.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
