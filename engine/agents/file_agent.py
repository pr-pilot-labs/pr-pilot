from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

import config
from core.event_log import EventLog
from engine.file_system import FileSystem
from engine.util import get_logger

logger = logging.getLogger(__name__)


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)



toolkit = FileManagementToolkit(
    root_dir=str(settings.REPO_DIR),
    selected_tools=["read_file", "write_file", "move_file", "copy_file"]

)

system_message = """
You are FileAgent. You handle requests to interact with the file system.
You must behave in the following way:
- When asked to read a file, ALWAYS return the entire file content
"""

template = """
File tree:
{file_tree}

Request:
{input}
"""

@tool
def talk_to_file_agent(prompt: str):
    """Talk to the file agent."""
    TaskEvent.add(actor="Darwin", action="talk_to", target="File Agent", message=prompt, transaction="begin")
    file_agent = create_file_agent()
    response = file_agent.invoke({"input": prompt, "file_tree": FileSystem().yaml()})
    TaskEvent.add(actor="Darwin", action="talk_to", target="File Agent", message=response['output'], transaction="end")
    return response['output']


def create_file_agent():

    prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], template=system_message)),
         HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
         MessagesPlaceholder(variable_name='agent_scratchpad')]
    )
    agent = create_openai_functions_agent(llm, toolkit.get_tools(), prompt)
    return AgentExecutor(agent=agent, tools=toolkit.get_tools(), verbose=settings.DEBUG)

