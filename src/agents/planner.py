from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from src.schemas import ProjectPlan
from src.config import GOOGLE_API_KEY, GEMINI_MODEL

PLANNER_SYSTEM = """You are a senior Django software architect.

Given a feature request, break it down into a concrete, minimal set of files
needed to implement it inside a single Django app. Prefer Django's built-in
patterns (class-based or function views, ModelForm/DRF-free serializers unless
DRF is explicitly requested, the ORM, django.contrib.admin) over third-party
packages. Only list a dependency if it is genuinely required.

Always include, at minimum: models.py, admin.py, urls.py, views.py, and a
tests.py with at least one meaningful test per model/view. Do not include
manage.py, settings.py, or the project-level urls.py - those already exist.
"""

def build_planner_chain():
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY, temperature=0.2)
    parser = PydanticOutputParser(pydantic_object=ProjectPlan)
    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_SYSTEM + "\n\n{format_instructions}"),
        ("human", "Build a plan for this Django feature request:\n\n{spec}"),
    ]).partial(format_instructions=parser.get_format_instructions())
    return prompt | llm | parser


def run_planner(spec: str) -> ProjectPlan:
    chain = build_planner_chain()
    return chain.invoke({"spec": spec})
