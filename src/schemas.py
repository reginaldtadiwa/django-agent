from typing import List, Literal
from pydantic import BaseModel, Field


# ---------- Planner ----------

class PlanStep(BaseModel):
    file_path: str = Field(description="Path relative to the app dir, e.g. 'models.py' or 'core/models.py'")
    description: str = Field(description="What this file must contain and why")
    component_type: Literal[
        "model", "view", "serializer", "url", "form", "admin", "test", "settings", "other"
    ]


class ProjectPlan(BaseModel):
    app_name: str
    summary: str = Field(description="One paragraph summary of what is being built")
    steps: List[PlanStep]
    dependencies: List[str] = Field(
        default_factory=list, description="Extra pip packages needed beyond Django itself, if any"
    )


# ---------- Coder ----------

class GeneratedFile(BaseModel):
    file_path: str = Field(description="Path relative to the Django project root, e.g. 'core/models.py'")
    content: str = Field(description="Complete file content. No placeholders, no TODOs, no ellipses.")
    explanation: str = Field(description="One sentence on what this file does")


class CoderOutput(BaseModel):
    files: List[GeneratedFile]


# ---------- Tester ----------

class TestResult(BaseModel):
    passed: bool
    summary: str
    failures: List[str] = Field(default_factory=list)
    raw_output: str = ""


# ---------- Reviewer ----------

class ReviewIssue(BaseModel):
    severity: Literal["critical", "major", "minor"]
    file_path: str
    issue: str
    suggestion: str


class ReviewResult(BaseModel):
    approved: bool
    issues: List[ReviewIssue] = Field(default_factory=list)
    summary: str
