from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic.v1 import BaseModel, Field

from prpilot import settings


class ContentMetaData(BaseModel):
    category: str = Field(..., title="Category")
    tags: list[str] = Field([], title="Tags")
    languages: list[str] = Field([], title="Languages")
    frameworks: list[str] = Field([], title="Frameworks")
    fa_icon_classes: str = Field("", title="Font Awesome Icon Classes")


system_message = """
You generate metadata for content.

Meta data consists of the following fields:
- Category - One of the following: "Content", "Code", "Utility", "Other"
- Languages - (Optional) A list of programming languages mentioned in the content, e.g. ["Python", "JavaScript", "HTML"]
- Frameworks - A list of frameworks mentioned in the content, e.g. ["Django", "React"]
- Tags - A list of EXACTLY THREE single-word tags that describe the content e.g. ["documentation", "api", "refactoring"]
- Tags should be different from the languages and frameworks mentioned
- Font Awesome Icon Classes - (Optional) A string of Font Awesome icon classes that represent the content, e.g. "fas fa-code"

Categories explained:
- Content: Anything that is related content creation or manipulation, e.g. writing, editing, etc.
- Code: Anything that is related to programming, e.g. writing code, debugging, etc.
- Utility: Anything that is related to tools, utilities, etc.
- Other: Anything that does not fit into the above categories.
---

# Content
{content}

---
Generate metadata for the content.
"""


def generate_metadata(content: str) -> ContentMetaData:
    prompt = PromptTemplate(
        template=system_message,
        input_variables=["issue_description", "user_request"],
    )
    model = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    chain = prompt | model.with_structured_output(ContentMetaData)
    return chain.invoke({"content": content})
