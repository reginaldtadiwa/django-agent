import json
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from src.schemas import ReviewResult, TestResult
from src.config import GOOGLE_API_KEY, GEMINI_MODEL

REVIEWER_SYSTEM = """You are a principal engineer performing a code review of
Django code, focused on correctness, security, and maintainability.

Specifically check for:
- SQL injection risk (raw SQL, .extra(), unparameterized queries)
- Missing input validation on forms/views
- Hardcoded secrets, API keys, or credentials
- Missing authentication/permission checks on views that modify data
- Mass assignment via unrestricted ModelForm fields
- N+1 query patterns in loops over querysets
- Missing CSRF protection where Django's default is disabled

Only set approved=false for "critical" or "major" issues. "minor" issues
(style, naming, missing docstrings) should be listed but must NOT block
approval on their own.
"""

def build_reviewer_chain():
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY, temperature=0.1)
    parser = PydanticOutputParser(pydantic_object=ReviewResult)
    prompt = ChatPromptTemplate.from_messages([
        ("system", REVIEWER_SYSTEM + "\n\n{format_instructions}"),
        ("human",
         "Test run result:\n{test_summary}\n\n"
         "Files to review:\n{files}\n\n"
         "Review this code now."),
    ]).partial(format_instructions=parser.get_format_instructions())
    return prompt | llm | parser


def run_reviewer(files: Dict[str, str], test_result: TestResult) -> ReviewResult:
    chain = build_reviewer_chain()
    test_summary = f"passed={test_result.passed}; {test_result.summary}"
    return chain.invoke({
        "test_summary": test_summary,
        "files": json.dumps(files, indent=2)[:12000],
    })
