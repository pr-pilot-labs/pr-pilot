import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from typing import List

import requests
from django.conf import settings
from git import Repo
from github import GithubException
from instructor import OpenAISchema
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import Field, BaseModel

from engine.code_analysis import generate_semgrep_report
from engine.file_system import FileSystem
from engine.langchain.generate_file import FileToGenerate, generate_file
from engine.models import TaskEvent, Task
from engine.project import Project
from engine.util import clean_code_block_with_language_specifier

logger = logging.getLogger(__name__)


class BasicTool(OpenAISchema):
    """A tool used by the Chat assistant to interact with the project."""

    def execute(self, state: dict):
        raise NotImplementedError

    @classmethod
    def all(cls):
        return cls.__subclasses__()

    @classmethod
    def from_function_call(cls, arguments: dict):
        return cls(**arguments)

#
# class ShowFileTree(WorkflowTool):
#     """Show the file tree of the project."""
#
#     keyword_filter: Optional[str] = Field(description="Filter the file tree to only show files containing this keyword")
#
#     def execute(self, state: dict):
#         file_system = FileSystem()
#         state["status_message"] = "Looking at file tree"
#         TaskEvent.add(actor="assistant", action="read_file_tree", message="Looking at project structure")
#         yaml_str = file_system.yaml(self.keyword_filter)
#         return yaml_str

#
# class ReadFile(WorkflowTool):
#     """Read the content of a specified file (will include line numbers)."""
#     path: str = Field(description="Path of the file to read")
#
#     def execute(self, state: dict):
#         file_system = FileSystem()
#         self.path = self.path.lstrip("/")
#         state["status_message"] = f"Reading `{self.path}`"
#         TaskEvent.add(actor="assistant", action="read_file", target=self.path)
#         node = file_system.get_node(Path(self.path))
#         if node:
#             # Add line numbers
#             logger.info(f"Reading file {self.path}")
#             with_lines = [f"{i + 1:4} | {line}" for i, line in enumerate(node.content.split('\n'))]
#             return f"[`{self.path}`, lines={len(with_lines)}]\n" + "\n".join(with_lines)
#         else:
#             return f"File not found: `{self.path}`"

class WriteNewFile(BasicTool):
    """Write given content to a file. Will fail if path already exists."""
    path: str = Field(description="Path of the new file")
    content: str = Field(description="Full content of the file end-to-end, line-by line. Leave nothing out.")

    def execute(self, state: dict):
        self.path = self.path.lstrip("/")
        file_system = FileSystem()
        if file_system.get_node(Path(self.path)):
            return f"File already exists: `{self.path}`. Not creating a new file."
        TaskEvent.add(actor="assistant", action="create_file", target=self.path, message=self.content)
        file_system.save(self.content, Path(self.path))
        Project.commit_all_changes(f"Add new file {self.path}")
        return f"Successfully created `{self.path}`"

class GenerateNewFiles(BasicTool):
    """Generate new content based on instructions and save the content into files. Make sure to provide enough context."""

    files: List[FileToGenerate] = Field(description="Maximum of 5 files to generate", max_length=5)

    def execute(self, state: dict):
        responses = ""
        with ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(generate_file, file): file for file in self.files}
            for future in as_completed(future_to_file):
                responses += future.result()
        return responses



class FileToEdit(BaseModel):
    """A file which should be edited"""
    path: str = Field(description="The path of the file")
    what_to_change: str = Field(description="Detailed description of what should be changed")

class EditFiles(BasicTool):
    """Make changes to a list of files."""

    files: List[FileToEdit] = Field(description="Maximum of 4 files to edit", max_length=4)

    def execute(self, state: dict):
        message = f""
        for file in self.files:
            message += f"**Editing `{file.path}`:**\n\n{file.what_to_change}\n\n"
        logger.info(f"Editing files: {message}")
        TaskEvent.add(actor="assistant", action="edit_files", message=message)
        model = ChatOpenAI(model="gpt-4-turbo-preview",
                           openai_api_key=settings.OPENAI_API_KEY) | StrOutputParser()
        responses = ""
        with ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(edit_file, file, model): file for file in self.files}
            for future in as_completed(future_to_file):
                responses += future.result()
        return responses
#
#
# class ListTODOs(WorkflowTool):
#     """Scan the project for TODO comments and return a list of file names and messages."""
#
#     def execute(self, state: dict):
#         state["status_message"] = "Looking for TODOs in the project"
#         file_system = FileSystem(settings.REPO_DIR)
#         todos = Todo.find_todos(file_system)
#         if len(todos) == 0:
#             return "No TODOs found in the project"
#         return "\n\n".join([f"#`{todo.file_path}`\n{todo.message}" for todo in todos])


class ListOpenGithubIssues(BasicTool):
    """List all open issues on the Github repo by number and title"""

    def execute(self, state: dict):
        state["status_message"] = "Looking for open issues on Github"
        g = Task.current().github
        repo = g.get_repo(Task.current().github_project)
        open_issues = repo.get_issues(state='open')
        not_prs = [issue for issue in open_issues if not issue.pull_request]
        if not not_prs:
            return "No open issues found"
        return "\n".join([f"- [{issue.number}] {issue.title}" for issue in not_prs])


class ReadGithubIssue(BasicTool):
    """Read the description and comments of a Github issue"""

    issue_number: int = Field(description="Number of the Github issue")

    def execute(self, state: dict):
        """Read the issue and return description + comments as markdown"""
        # Initialize GitHub client
        state["status_message"] = f"Reading Github issue #{self.issue_number}"
        g = Task.current().github
        repo = g.get_repo(Task.current().github_project)

        issue = repo.get_issue(int(self.issue_number))

        # Prepare the markdown string
        markdown_output = f"## Issue Description\n{issue.body}\n\n## Comments\n"
        for comment in issue.get_comments():
            markdown_output += f"**{comment.user.login} wrote:**\n{comment.body}\n\n"

        return markdown_output


# class ListDirectory(WorkflowTool):
#     """List the contents of a directory"""
#
#     path: str = Field(description="Path of the directory to list")
#
#     def execute(self, state: dict):
#         file_system = FileSystem()
#         node = file_system.get_node(Path(self.path))
#         if not node:
#             return f"Directory not found: `{self.path}`"
#         if not node.is_directory:
#             return f"Path is not a directory: `{self.path}`"
#         return "\n".join([f"- {child.name}{'/' if child.is_directory else ''}" for child in node.nodes])

class AddCommentToGithubIssue(BasicTool):
    """Add a comment to a Github issue.  ONLY use this if explicitly requested by the user."""

    issue_number: int = Field(description="Number of the Github issue")
    comment: str = Field(description="The comment, markdown-formatted")

    def execute(self, state: dict):
        state["status_message"] = f"Commenting on Github issue #{self.issue_number}"
        g = Task.current().github
        repo = g.get_repo(Task.current().github_project)
        issue = repo.get_issue(self.issue_number)
        comment = issue.create_comment(self.comment)
        TaskEvent.add(actor="assistant", action="add_github_comment", target=str(issue.id),
                           message=f"Commented on [Issue {issue.number}]({issue.html_url})")
        return f"Comment added successfully to issue {self.issue_number} : {comment.html_url}"


class CreateGithubIssue(BasicTool):
    """Create a new Github issue. ONLY use this if explicitly requested by the user."""

    title: str = Field(description="Title of the Github issue")
    body: str = Field(description="The body of the issue, markdown-formatted")
    labels: list[str] = Field(description="List of labels to add to the issue", default=[])

    def execute(self, state: dict):
        state["status_message"] = f"Creating Github Issue"
        g = Task.current().github
        repo = g.get_repo(Task.current().github_project)
        self.labels.append("darwin")
        try:
            issue = repo.create_issue(title=self.title, body=self.body, labels=self.labels)
        except GithubException as e:
            TaskEvent.add(actor="assistant", action="create_github_issue",
                               message=f"Failed to create Github issue `{self.title}`: {e.message}")
            return f"Failed to create Github issue `{self.title}`: {e.message}"
        TaskEvent.add(actor="assistant", action="create_github_issue", target=f"#{issue.number} - {issue.title}",
                           message=f"Created [Issue #{issue.number}]({issue.html_url})")
        return f"Issue created successfully : {issue.html_url}"


class LookAtGitHistory(BasicTool):
    """Look at the git history of the project."""

    branch: str = Field(description="Which branch to look at", default=Repo(settings.REPO_DIR).active_branch.name)

    def execute(self, state: dict):
        state["status_message"] = f"Looking at git history"
        TaskEvent.add(actor="assistant", action="look_at_git_history")
        repo = Repo(settings.REPO_DIR)
        commits = repo.iter_commits(self.branch)
        max_commits = 20
        commits = [commit for commit in commits][:max_commits]

        full_message = ""
        for commit in commits:
            changed_files = [f"- {file}" for file in commit.stats.files.keys()]
            full_message += f"# {commit.committed_datetime}\n```\n{commit.message}\n```\n\n{changed_files}\n\n"
        return full_message


class RunSecurityScan(BasicTool):
    """Scan the project for security vulnerabilities and return a report, listing all files and their vulnerabilities (if any)."""

    def execute(self, state: dict):
        state["status_message"] = f"Running Code Analysis with Semgrep"
        TaskEvent.add(actor="assistant", action="security_scan", message="Running Security scan with semgrep")
        return generate_semgrep_report("p/security-audit")


class Framework(Enum):
    """Supported frameworks for scanning for framework-specific issues"""
    DJANGO = "django"
    FLASK = "flask"


class ScanForFrameworkSpecificIssues(BasicTool):
    """Scan the project for framework-specific issues and return a report, listing all files and their issues (if any)."""

    framework: Framework = Field(description="The framework to scan for issues")

    def execute(self, state: dict):
        state["status_message"] = f"Running Code Analysis with Semgrep"
        TaskEvent.add(actor="assistant", action="code_scan", message=f"Scanning for {self.framework.value}-related issues")
        return generate_semgrep_report(f"p/{self.framework.value}")

class Language(Enum):
    """Supported languages for scanning for language-specific issues"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    PHP = "php"

class ScanForLanguageSpecificIssues(BasicTool):
    """Scan the project for language-specific issues and return a report, listing all files and their issues (if any)."""

    language: Language = Field(description="The framework to scan for issues")

    def execute(self, state: dict):
        TaskEvent.add(actor="assistant", action="code_scan", message=f"Scanning for {self.language.value}-related issues")
        return generate_semgrep_report(f"p/{self.language.value}")


def create_github_wiki_page(access_token, repo, page_path, content, message, email, name):
    """
    Create or update a GitHub wiki page.

    Parameters:
    - access_token: Your GitHub personal access token
    - repo: Repository name with owner (e.g., "owner/repo")
    - page_path: Path to the wiki page to create or update (e.g., "Home.md")
    - content: Content of the wiki page
    - message: Commit message for the update
    - email: Your email associated with the GitHub commit
    - name: Your name associated with the GitHub commit
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{page_path}"
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {
        "message": message,
        "committer": {
            "name": name,
            "email": email
        },
        "content": encoded_content
    }
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.put(api_url, json=data, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        logger.info("Wiki page created or updated successfully.")
        return response.json()
    else:
        logger.info(f"Failed to create or update wiki page. Status code: {response.status_code}, Response: {response.text}")
        return None

#
# class CreateGithubWikiPage(WorkflowTool):
#     """Create a new Github wiki page. ONLY use this if explicitly requested by the user."""
#
#     title: str = Field(description="Title of the Github wiki page")
#     content: str = Field(description="The content of the wiki page, markdown-formatted")
#
#     def execute(self, state: dict):
#         state["status_message"] = f"Creating Github Wiki Page"
#         g = Task.current().github
#         g.get_user()
#         repo = g.get_repo(Task.current().github_project)
#         user = g.get_user()
#         name = user.name
#         email = user.email
#         page = create_github_wiki_page(Credentials.load().get(Credentials.GITHUB_ACCESS_TOKEN), Task.current().github_project, f"{self.title}.md", self.content, "Created Wiki Page", email, name)
#         if not page:
#             return f"Failed to create wiki page"
#         TaskEvent.add(actor="assistant", action="create_github_wiki_page", target=str(page.id),
#                            message=f"Created [Wiki Page {self.title}]({page.html_url})")
#         return f"Wiki page created successfully : {page.html_url}"


class FileToInspect(BaseModel):
    """A file to inspect"""
    path: str = Field(description="The path of the file to inspect")
    what_to_inspect: str = Field(description="Detailed description of what we want to know about the file")

class InspectFiles(BasicTool):
    """Extract information from a list of files. This is an expensive operation. Use it only when necessary."""

    files: List[FileToInspect] = Field(description="Maximum of 4 files to inspect", max_length=4)

    def execute(self, state: dict):
        message = f""
        for file in self.files:
            message += f"**Inspecting `{file.path}`:**\n\n{file.what_to_inspect}\n\n"
        logger.info(f"Inspecting files: {message}")
        TaskEvent.add(actor="assistant", action="inspect_files", message=message)
        responses = run_in_threadpool(self.files)
        return responses

def inspect_file(file, model):
    response = f"# `{file.path}`\n"
    file_node = FileSystem().get_node(Path(file.path))
    if not file_node:
        TaskEvent.add(actor="assistant", action="inspect_file", target=file.path, message="File not found")
        response += "File not found\n\n"
        return response
    prompt = (f"You extract information about a file."
              f"# File `{file}`\n{file_node.content}\n\n"
              f"# What do you want to know about this file?\n{file.what_to_inspect}\n\n"
              f"Extracted Information:\n")
    response += model.invoke(prompt)
    return response

def edit_file(file, model):
    file_node = FileSystem().get_node(Path(file.path))
    if not file_node:
        TaskEvent.add(actor="assistant", action="edit_file", target=file.path, message="File not found")
        return f"File not found: `{file}`"
    prompt = (f"You make changes to a file."
              f"# File `{file}`\n{file_node.content}\n\n"
              f"# What do you want to change in this file?\n{file.what_to_change}\n\n"
              f"# Full, changed content of the file (no additional text)\n")
    new_file_content = clean_code_block_with_language_specifier(model.invoke(prompt))
    FileSystem().save(new_file_content, Path(file.path))
    Project.commit_changes_of_file(Path(file.path), file.what_to_change)
    return f"Changes saved to `{file}`"

def run_in_threadpool(files):
    responses = ""
    model = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=settings.OPENAI_API_KEY) | StrOutputParser()
    with ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(inspect_file, file, model): file for file in files}
        for future in as_completed(future_to_file):
            responses += future.result()
    return responses