import logging

from django.conf import settings
from langchain_community.llms.openai import OpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


system_message = """
We need to run a task based on a Github issue description and a user request.

# Issue description
{issue_description}

# User request
{user_request}

The task title should be no more than 10 words!

Title:
"""
prompt = PromptTemplate(
    template=system_message,
    input_variables=["issue_description", "user_request"],
)


parser = StrOutputParser()
model = OpenAI(model="gpt-3.5-turbo", openai_api_key=settings.OPENAI_API_KEY, temperature=0)
chain = prompt | model | parser


def generate_task_title(issue_description: str, user_request: str) -> str:
    return chain.invoke({"issue_description": issue_description, "user_request": user_request})
