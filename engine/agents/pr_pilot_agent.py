import logging
from pathlib import Path
from typing import Optional

from django.conf import settings
from github.GithubObject import Opt, NotSet
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from engine.agents.analysis_agent import talk_to_analysis_agent_agent
from engine.agents.common import AGENT_COMMUNICATION_RULES
from engine.agents.github_agent import read_github_issue, read_pull_request
from engine.agents.web_search_agent import talk_to_web_search_agent
from engine.file_system import FileSystem
from engine.langchain.cost_tracking import CostTrackerCallback
from engine.models import TaskEvent, Task
from engine.project import Project

logger = logging.getLogger(__name__)




system_message = """
You are PR Pilot, an AI agent that works on Github issues and PRs.

# How to handle files
- Reading files is EXPENSIVE. Only read the files you really need to solve the task
- When writing files, ALWAYS write the entire file content, do not leave anything out.

# Searching the code base
You can search the code base using the `search_github_code` function. It uses the Github search syntax.
Use this function to find out more about classes/functions/files/etc mentioned in the user request.

## Example 1: Search for `initMap` function in JavaScript files
`symbol:initMap language:javascript`

## Example 2: Find all `WithContext` functions in Go files
`language:go symbol:WithContext`

## Example 3: Locate `TODO` comments in Python files
`TODO language:python`

## Example 4: Search for `NullPointerException` in Java files
`NullPointerException language:java`

## Example 5: Find all JavaScript files in the `src` directory and its subdirectories
`path:/src/**/*.js`

## Example 6: FInd all files with the `.txt` extension
`path:*.txt`


# How to talk to WebSearchAgent
You can talk to the WebSearchAgent using the `talk_to_web_search_agent` function. Make sure to ask detailed, specific
questions to get the best results. Use full sentences and give enough context.

Examples:
- "Visit URL <url> and tell me <what you want to know>"
- "Search for <search query>, visit the top 3 results and answer my question: <what you want to know>"

""" + AGENT_COMMUNICATION_RULES

template = """
# Name of the Github project this request is from
{github_project}

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
def write_file(path: str, complete_entire_file_content: str, commit_message: str):
    """Write content to a file.
    :param path: Path to the file
    :param complete_entire_file_content: Complete content of the file. NEVER use placeholders or partial content.
    :param commit_message: Short commit message for the change
    """
    path = path.lstrip("/")
    file_system = FileSystem()
    # if file_system.get_node(Path(path)):
    #     return f"File already exists: `{path}`. Not creating a new file."
    TaskEvent.add(actor="assistant", action="write_file", target=path)
    file_system.save(complete_entire_file_content, Path(path))
    Project.commit_all_changes(commit_message)
    return f"Successfully wrote content to `{path}`"

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


@tool
def search_github_code(query: str, sort: Optional[str], order: Optional[str]):
    """Search for code in the repository.
        :param query: Search query in Github search syntax
        :param sort: string ('indexed')
        :param order: string ('asc', 'desc')
    """
    g = Task.current().github
    # Force query to use the repository name
    query = f"repo:{Task.current().github_project} {query}"

    results = g.search_code(query, sort=sort, order=order)
    if not results.totalCount:
        TaskEvent.add(actor="assistant", action="search_code", message=f"Searched code with query: `{query}`. No results.")
        return "No code found"

    response = ""
    relevant_files = ""
    for result in results:
        relevant_files += f"- `{result.path}`\n"
        for match in result.text_matches:
            response += f"**Match in `{result.path}`**\n"
            response += f"```\n{match['fragment']}\n```\n\n"
    TaskEvent.add(actor="assistant", action="search_code", message=f"Searched code with query: `{query}`. Found {results.totalCount} results:\n\n{relevant_files}")
    return response


@tool
def search_github_issues(query: str, sort: Optional[str], order: Optional[str]):
    """Search for issues in the repository.
    :param query: Search query in Github search syntax
    :param sort: string ('created', 'updated', 'comments')
    :param order: string ('asc', 'desc')
    """
    g = Task.current().github
    # Force query to use the repository name
    query = f"{query} repo:{Task.current().github_project}"
    results = g.search_issues(query, sort=sort, order=order)
    if not results.totalCount:
        TaskEvent.add(actor="assistant", action="search_issues", message=f"Searched issues with query: `{query}`. No results.")
        return "No issues found"
    response = ""
    for result in results:
        response += f"**Issue #{result.number}**\n"
        response += f"[{result.title}]({result.html_url})\n\n"
    TaskEvent.add(actor="assistant", action="search_issues", message=f"Searched issues with query: `{query}`. Found {results.totalCount} results:\n\n{response}")
    return response


def create_pr_pilot_agent():
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0, callbacks=[CostTrackerCallback("gpt-4-turbo-preview", "Tool Execution")])
    tools = [read_github_issue, read_pull_request, talk_to_web_search_agent, create_directory, write_file, read_files, search_github_code, search_github_issues] + file_tools
    prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], template=system_message)),
         HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['user_request', 'github_project'], template=template)),
         MessagesPlaceholder(variable_name='agent_scratchpad'),
         SystemMessage('Fulfill the user request autonomously and provide the response, without asking for further input. If anything fails along the way, abort and provide a reason.')]
    )
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG)

