import argparse
import os
import subprocess
import sys

from src.graph import build_graph
from src.config import PROJECT_OUTPUT_DIR


def bootstrap_django_project(project_dir: str, app_name: str) -> None:
    """Creates the real Django scaffold (manage.py, settings.py, the app dir)
    via django-admin, so the agents only ever write feature code, never the
    boilerplate Django needs to boot at all."""
    os.makedirs(project_dir, exist_ok=True)

    if not os.path.exists(os.path.join(project_dir, "manage.py")):
        subprocess.run(
            [sys.executable, "-m", "django", "startproject", "config", "."],
            cwd=project_dir, check=True,
        )

    app_path = os.path.join(project_dir, app_name)
    if not os.path.exists(app_path):
        subprocess.run(
            [sys.executable, "manage.py", "startapp", app_name],
            cwd=project_dir, check=True,
        )
        _register_app(project_dir, app_name)


def _register_app(project_dir: str, app_name: str) -> None:
    settings_path = os.path.join(project_dir, "config", "settings.py")
    with open(settings_path) as f:
        content = f.read()
    if f"'{app_name}'" not in content:
        content = content.replace("INSTALLED_APPS = [", f"INSTALLED_APPS = [\n    '{app_name}',")
        with open(settings_path, "w") as f:
            f.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Planner -> Coder -> Tester -> Reviewer agent pipeline that "
                     "builds a real, runnable Django feature."
    )
    parser.add_argument("spec", help="Natural language description of the feature to build")
    parser.add_argument("--app-name", default="core", help="Django app name (default: core)")
    parser.add_argument("--project-dir", default=PROJECT_OUTPUT_DIR, help="Where to write the project")
    args = parser.parse_args()

    print(f"Bootstrapping Django project at {os.path.abspath(args.project_dir)} ...")
    bootstrap_django_project(args.project_dir, args.app_name)

    graph = build_graph()
    initial_state = {
        "spec": f"App name: {args.app_name}\n\nFeature request:\n{args.spec}",
        "project_dir": args.project_dir,
        "plan": None,
        "files": {},
        "test_result": None,
        "review_result": None,
        "iteration": 0,
        "feedback": "",
        "log": [],
    }

    final_state = graph.invoke(initial_state, config={"recursion_limit": 50})

    print("\n" + "=" * 60)
    print("RUN LOG")
    print("=" * 60)
    for line in final_state["log"]:
        print(line)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Iterations used: {final_state['iteration']} / {os.getenv('MAX_ITERATIONS', '3')}")
    if final_state["test_result"]:
        print(f"Tests:  {'PASSED' if final_state['test_result'].passed else 'FAILED'}")
    if final_state["review_result"]:
        status = "APPROVED" if final_state["review_result"].approved else "CHANGES REQUESTED"
        print(f"Review: {status}")
    print(f"Project written to: {os.path.abspath(args.project_dir)}")
    print(f"Run it with: cd {args.project_dir} && python manage.py runserver")


if __name__ == "__main__":
    main()
