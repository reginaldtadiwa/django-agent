from typing import Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from src.agents.planner import run_planner
from src.agents.coder import run_coder
from src.agents.tester import run_tester, write_files_to_disk
from src.agents.reviewer import run_reviewer
from src.schemas import ProjectPlan, TestResult, ReviewResult
from src.config import MAX_ITERATIONS


class AgentState(TypedDict):
    spec: str
    project_dir: str
    plan: Optional[ProjectPlan]
    files: Dict[str, str]
    test_result: Optional[TestResult]
    review_result: Optional[ReviewResult]
    iteration: int
    feedback: str
    log: List[str]


def planner_node(state: AgentState) -> AgentState:
    plan = run_planner(state["spec"])
    state["plan"] = plan
    state["log"].append(f"[planner] {len(plan.steps)} file(s) planned for app '{plan.app_name}'")
    return state


def coder_node(state: AgentState) -> AgentState:
    output = run_coder(state["plan"], state["files"], state["feedback"])
    for f in output.files:
        state["files"][f.file_path] = f.content
    state["log"].append(f"[coder] wrote/updated {len(output.files)} file(s)")
    return state


def tester_node(state: AgentState) -> AgentState:
    write_files_to_disk(state["files"], state["project_dir"])
    result = run_tester(state["project_dir"])
    state["test_result"] = result
    state["log"].append(f"[tester] passed={result.passed} - {result.summary}")
    return state


def reviewer_node(state: AgentState) -> AgentState:
    result = run_reviewer(state["files"], state["test_result"])
    state["review_result"] = result
    state["log"].append(
        f"[reviewer] approved={result.approved} - {len(result.issues)} issue(s) - {result.summary}"
    )
    return state


def route_after_review(state: AgentState) -> str:
    tests_ok = state["test_result"].passed
    review_ok = state["review_result"].approved

    if tests_ok and review_ok:
        return "done"

    if state["iteration"] >= MAX_ITERATIONS:
        return "give_up"

    # Build concrete feedback for the coder's next pass
    feedback_parts = []
    if not tests_ok:
        feedback_parts.append("TEST FAILURES:\n" + "\n---\n".join(state["test_result"].failures))
    if not review_ok:
        blocking = [i for i in state["review_result"].issues if i.severity in ("critical", "major")]
        feedback_parts.append(
            "REVIEW ISSUES:\n" + "\n".join(
                f"[{i.severity}] {i.file_path}: {i.issue} -> {i.suggestion}" for i in blocking
            )
        )
    state["feedback"] = "\n\n".join(feedback_parts)
    state["iteration"] += 1
    return "revise"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner_node)
    g.add_node("coder", coder_node)
    g.add_node("tester", tester_node)
    g.add_node("reviewer", reviewer_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "coder")
    g.add_edge("coder", "tester")
    g.add_edge("tester", "reviewer")
    g.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"done": END, "give_up": END, "revise": "coder"},
    )
    return g.compile()
