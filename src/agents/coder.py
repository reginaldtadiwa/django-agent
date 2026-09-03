import json
from typing import Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from src.schemas import ProjectPlan, CoderOutput
from src.config import GOOGLE_API_KEY, GEMINI_MODEL

CODER_SYSTEM = """You are a senior Django developer implementing an approved plan.

Rules:
- Write COMPLETE file contents. No "...", no "# TODO", no truncation.
- Every file must be valid, importable Python (or a valid Django template).
- Include all needed imports.
- Follow the plan's file paths exactly, relative to the Django project root
  (e.g. 'core/models.py', 'core/views.py').
- If feedback from failed tests or a code review is provided, fix the root
  cause, don't just patch symptoms. Re-emit every file that needs to change,
  including ones you already wrote, in full.
- Do not touch manage.py, config/settings.py, or config/urls.py.
"""

def build_coder_chain():
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY, temperature=0.1)
    parser = PydanticOutputParser(pydantic_object=CoderOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", CODER_SYSTEM + "\n\n{format_instructions}"),
        ("human",
         "Plan:\n{plan}\n\n"
         "Files written so far (may be empty on first pass):\n{existing_files}\n\n"
         "Feedback to address (empty if this is the first pass):\n{feedback}\n\n"
         "Write or rewrite every file needed now."),
    ]).partial(format_instructions=parser.get_format_instructions())
    return prompt | llm | parser


def run_coder(plan: ProjectPlan, existing_files: Dict[str, str], feedback: Optional[str]) -> CoderOutput:
    chain = build_coder_chain()
    return chain.invoke({
        "plan": plan.model_dump_json(indent=2),
        "existing_files": json.dumps(existing_files, indent=2) if existing_files else "None yet",
        "feedback": feedback or "None - this is the first implementation pass.",
    })
