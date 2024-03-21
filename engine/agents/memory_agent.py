import logging
from typing import List

import django

django.setup()
from django.conf import settings
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from engine.langchain.cost_tracking import CostTrackerCallback
from engine.memory.memory import insert_memory, Memory, search_memories
from engine.models import TaskEvent, Task

logger = logging.getLogger(__name__)



system_message = """
You are MemoryAgent.
You are part of "PR Pilot", an AI assistant for Github. PR Pilot executes tasks for Github users 
and provides them with the results. You are responsible for managing the memories of the assistant.
After a task is run, you will be provided with the following info:
- The initial query/command of the user
- The result of the task
- The actions taken by PR Pilot as part of the task

You need to create memories based on the information provided. Memories should capture knowledge about the Github project
that can be retrieved in future task executions in order to improve PR Pilot's usefulness over time.

Memories should fall into the following categories:
- "user_preference" - Memories that capture the preferences of the user
- "library - Memorize the usage of a library in the Github project
- "framework" - Memorize that the project is based on some framework
- "class" - Memorize the usage of a class, its purpose and relationship to other parts of the codebase

You can create memories using the `create_memories` tool. Here are a few good examples:

- **user_preference** The user prefers to use `pytest` for testing
- **library** The project uses `pandas` for analyzing <some specific data> in <some specific file>
- **framework** The project uses `Django` as webframework and has defined Django apps in <some specific directories>
- **class** The project uses a `Backlog` class to manage a list of tasks and their status as files in <some specific directory>

Guidelines for memory creation:
- Only create memories that aren't already present in the memory database
- Only create memories if the task contains information that fits into the given categories
- Do not mention Github project names in the memories
- If no new memories are needed, you can skip memory creation

You can search for existing memories using the `retrieve_memories` tool.
Here are a few good example queries:
- "Usage of `Backlog` class, `pytest` for testing, and `Django` as webframework"
- "Usage of `pandas` for analyzing data and classes related to data processing"
- "User preferences for testing and webframeworks"

# How do formulate your response
When responding to a request for memories, make sure your response is specific to the user request and 
does NOT contain any information that wasn't asked for.

## Example
Your search returned the following relevant memories:
- **class** The project uses a `TaskEngine` class to manage and execute tasks.
- **userpreference** The user prefers to use `pytest` for testing.
 
If the request was about the TaskEngine, do not mention the user preference memory in your response.
"""


@tool
def create_memories(memories: List[Memory]):
    """Create new memories."""
    for memory in memories:
        insert_memory(memory.text, memory.category.value, Task.current())
    memories_markdown = "\n".join([f"- **{memory.category.value.replace('_', '')}** {memory.text})" for memory in memories])
    return "Memories created."


@tool
def retrieve_memories(prompt: str):
    """Retrieve memories. The search results' relevance is based on cosine similarity."""
    results = search_memories(prompt, Task.current(), top_k=5)
    if len(results) == 0:
        return "No relevant memories found."
    markdown = "Relevant memories:\n"
    for result in results:
        markdown += f"- **{result.memory.category.value.replace('_', '')}** {result.memory.text} (score: {result.score})\n"
    return markdown


@tool
def talk_to_memory_agent_agent(prompt: str):
    """Talk to the Memory agent."""
    github_agent = create_memory_agent()
    response = github_agent.invoke({"input": prompt})
    return response['output']



def create_memory_agent():
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0, callbacks=[CostTrackerCallback("gpt-4-turbo-preview", "create memories")])
    tools = [create_memories, retrieve_memories]

    prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], template=system_message)),
         HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
         MessagesPlaceholder(variable_name='agent_scratchpad')]
    )
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG)


if __name__ == '__main__':
    task = Task.objects.order_by('?').first()
    settings.TASK_ID = task.id
    result = talk_to_memory_agent_agent(f"Search for relevant memories for this task and - if necessary - create new memoris\n\n{task.to_markdown()}")
    print(result)
