import os
import subprocess
from typing import Dict, List, Tuple

from src.schemas import TestResult


def write_files_to_disk(files: Dict[str, str], project_dir: str) -> None:
    for rel_path, content in files.items():
        full_path = os.path.join(project_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)


def _run(cmd: List[str], cwd: str, timeout: int = 120) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"Command timed out after {timeout}s: {e}"
    except FileNotFoundError as e:
        return -1, "", f"Command not found: {e}"


def run_tester(project_dir: str) -> TestResult:
    """
    Actually executes the generated Django project rather than asking an LLM
    to guess whether the code works. This is what makes the pipeline deliver
    'running software' instead of plausible-looking code.
    """
    failures: List[str] = []
    output_sections: List[str] = []

    # 1. System check - catches import errors, misconfigured models, bad URLs
    rc, out, err = _run(["python", "manage.py", "check"], project_dir)
    output_sections.append(f"$ manage.py check\n{out}{err}")
    if rc != 0:
        failures.append(f"System check failed (exit {rc}):\n{(err or out).strip()[:1500]}")

    # 2. Migration consistency - catches models that don't match migrations
    rc, out, err = _run(["python", "manage.py", "makemigrations", "--check", "--dry-run"], project_dir)
    output_sections.append(f"$ manage.py makemigrations --check --dry-run\n{out}{err}")
    if rc != 0:
        failures.append(
            "Model changes are missing migrations. Run 'manage.py makemigrations' "
            f"or fix the model definitions:\n{(err or out).strip()[:1000]}"
        )

    # 3. Actual test suite
    rc, out, err = _run(["python", "manage.py", "test", "-v", "2"], project_dir, timeout=180)
    output_sections.append(f"$ manage.py test -v 2\n{out}{err}")
    if rc != 0:
        failures.append(f"Test suite failed (exit {rc}):\n{(err or out).strip()[:2000]}")

    raw_output = "\n\n".join(output_sections)
    passed = len(failures) == 0

    return TestResult(
        passed=passed,
        summary="All system checks, migration checks, and tests passed."
        if passed else f"{len(failures)} issue(s) found - see failures.",
        failures=failures,
        raw_output=raw_output[:6000],
    )
