import logging
from pathlib import Path

from django.conf import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from engine.file_system import FileSystem
from engine.models import TaskEvent
from engine.project import Project
from engine.util import clean_code_block_with_language_specifier

logger = logging.Logger(__name__)

class FileToGenerate(BaseModel):
    """A file to generate"""
    path: str = Field(description="The path of the file to generate")
    what_to_generate: str = Field(description="Description of what will be generated as file content")


system_message = """
You generate the content of a new file based instructions."""
prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    ("user", "{input}"),
    ("system", "Respond with the full content of the file, nothing else"),
])
model = ChatOpenAI(model="gpt-4-turbo-preview", openai_api_key=settings.OPENAI_API_KEY)
chain = prompt | model | StrOutputParser()


def generate_file(file_to_generate: FileToGenerate):
    logger.info(f"Generating file {file_to_generate.path}")
    TaskEvent.add(actor="assistant", action="generate_file", target=file_to_generate.path, message=file_to_generate.what_to_generate)
    file_node = FileSystem().get_node(Path(file_to_generate.path))
    if file_node:
        msg = f"FAILED to generate `{file_to_generate.path}`. File already exists!"
        TaskEvent.add(actor="assistant", action="generate_file", target=file_to_generate.path, message=msg)
        return msg
    generated_content = clean_code_block_with_language_specifier(chain.invoke({"input": file_to_generate.what_to_generate}))
    if not generated_content:
        msg = f"FAILED to generate `{file_to_generate.path}`. No content was generated!"
        TaskEvent.add(actor="assistant", action="generate_file", target=file_to_generate.path, message=msg)
        return msg
    FileSystem().save(generated_content, Path(file_to_generate.path))
    Project.commit_changes_of_file(Path(file_to_generate.path), f"Generated file\n\nInstructions:\n{file_to_generate.what_to_generate}")
    return f"File `{file_to_generate.path}` generated successfully"

if __name__ == '__main__':
    file_to_generate = FileToGenerate(path="file.txt", what_to_generate="A Pydantic model to represent 'settings' as key-value pairs")
    print(generate_file(file_to_generate))