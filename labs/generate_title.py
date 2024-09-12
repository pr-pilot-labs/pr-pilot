import logging

from django.conf import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


MAX_TITLE_LENGTH = 100

system_message = """
You generate titles for AI experiments.
You will get a description of the experiment and generate a title for it.

# Examples
Here are examples of what good task titles look like

- "Check if documentation is still up-to-date"
- "Add a new feature to the dashboard"
- "Update the API documentation"
- "Refactor the user management code"

# Experiment

## Github project
{github_project}

{github_project_description}

## Agent Knowledge for the experiment
{knowledge}

## Instructions for the experiment
{instructions}


Task Title:
"""


def generate_experiment_title(
    github_project: str,
    github_project_description: str,
    knowledge: str,
    instructions: str,
) -> str:
    prompt = PromptTemplate(
        template=system_message,
        input_variables=["issue_description", "user_request"],
    )
    parser = StrOutputParser()
    model = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=1,
    )
    chain = prompt | model | parser
    return (
        chain.invoke(
            {
                "github_project": github_project,
                "github_project_description": github_project_description,
                "knowledge": knowledge,
                "instructions": instructions,
            }
        )
        .replace("\n", "")
        .lstrip('"')
        .rstrip('"')[:MAX_TITLE_LENGTH]
    )
