import logging
from pathlib import Path

from django.conf import settings
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from engine.agents.analysis_agent import talk_to_analysis_agent_agent
from engine.agents.common import AGENT_COMMUNICATION_RULES
from engine.agents.github_agent import talk_to_github_agent
from engine.agents.web_search_agent import talk_to_web_search_agent
from engine.file_system import FileSystem
from engine.langchain.cost_tracking import CostTrackerCallback
from engine.models import TaskEvent
from engine.project import Project

logger = logging.getLogger(__name__)




system_message = """
You are PR Pilot, an AI agent that works on Github issues and PRs.

You do your work by talking to the following agents:
- GithubAgent: Can interact with Github issues and pull requests
- WebSearchAgent: Finds information on the web
- AnalysisAgent: Analyzes the code base for potential issues and insights

To interact with the file system, use your own functions.

# How to handle files
- Reading files is EXPENSIVE. Only read the files you really need to solve the task
- When writing files, ALWAYS write the entire file content, do not leave anything out.


""" + AGENT_COMMUNICATION_RULES

template = """
# User Request

{user_request}
"""

file_tools = FileManagementToolkit(
    root_dir=str(settings.REPO_DIR),
    selected_tools=["move_file", "copy_file"]

).get_tools()


@tool
def search_files(keyword: str):
    """Search for files in the project."""
    all_files = FileSystem().list_files()
    found_files = [str(file).replace(str(settings.REPO_DIR), '').lstrip('/') for file in all_files if keyword in str(file.name)]
    if len(found_files) > settings.MAX_FILE_SEARCH_RESULTS:
        return f"Too many files ({len(found_files)}) found for keyword '{keyword}'. Please refine your search."
    if found_files:
        return "\n".join(found_files)
    else:
        return "No files found."


@tool
def create_directory(path: str):
    """Create a directory and all parent directories if they do not exist."""
    TaskEvent.add(actor="Darwin", action="create_directory", target=path, message=f"Creating directory {path}")
    FileSystem().create_directory(path)
    return f"Directory {path} created."

@tool
def write_file(path: str, complete_entire_file_content: str):
    """Write content to a file. IMPORTANT: Do not truncate the file, always write the entire content."""
    path = path.lstrip("/")
    file_system = FileSystem()
    # if file_system.get_node(Path(path)):
    #     return f"File already exists: `{path}`. Not creating a new file."
    TaskEvent.add(actor="assistant", action="write_file", target=path)
    file_system.save(complete_entire_file_content, Path(path))
    Project.commit_all_changes(f"Add new file {path}")
    return f"Successfully created `{path}`"

@tool
def read_files(file_paths: list[str]):
    """Read the content of the given files."""
    if len(file_paths) > settings.MAX_READ_FILES:
        return f"Too many files ({len(file_paths)}) to read. Please limit to {settings.MAX_READ_FILES} files."
    file_system = FileSystem()
    message = "Reading files: \n" + "\n- ".join(f"`{file_path}`\n" for file_path in file_paths)
    TaskEvent.add(actor="assistant", action="read_files", message=message)
    output = ""
    for file_path in file_paths:
        file_path = file_path.lstrip("/")
        file_node = file_system.get_node(Path(file_path))
        if file_node:
            output += f"### {file_path}\n"
            output += file_node.content
            output += "\n\n"
        else:
            output += f"File not found: `{file_path}`\n"
    non_empty_line_count = len([line for line in output.split("\n") if line.strip()])
    if non_empty_line_count > settings.MAX_FILE_LINES:
        return f"The content of {file_paths} is longer than {settings.MAX_FILE_LINES} lines and too expensive to analyze. Abort!"
    return output

def create_pr_pilot_agent():
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0, callbacks=[CostTrackerCallback("gpt-4-turbo-preview", "Tool Execution")])
    tools = [talk_to_github_agent, talk_to_web_search_agent, talk_to_analysis_agent_agent, create_directory, write_file, read_files, search_files] + file_tools
    prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], template=system_message)),
         HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['user_request'], template=template)),
         MessagesPlaceholder(variable_name='agent_scratchpad'),
         SystemMessage('Fulfill the user request autonomously and provide the result, without asking for further input. If anything fails along the way, abort and provide a reason.')]
    )
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG)

