import logging
from typing import List

from django.conf import settings
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from engine.langchain.cost_tracking import CostTrackerCallback
from engine.memory.memory import insert_memory, Memory, search_memories
from engine.models import Task, TaskEvent

logger = logging.getLogger(__name__)



system_message = """
You are MemoryAgent.
You are part of "PR Pilot", an AI assistant for Github. PR Pilot executes tasks for Github users 
and provides them with the results. You are responsible for managing the memories of the assistant.

Before a task is run, you will be provided with the following info:
- The context of the task (a Github issue/PR)
- The initial query/command of the user

We store the memories in a vector store using a SentenceTransformer model.
You help find relevant information by forming queries that find information which will help solve the task.

You can search memories using the `retrieve_memories` tool.
Here are a few good example queries:
- "Usage of `Backlog` class, `pytest` for testing, and `Django` as webframework"
- "Usage of `pandas` for analyzing data and classes related to data processing"
- "User preferences for testing and webframeworks"

# How to interpret memories
Retrieved memory have a "score" which is based on cosine similarity. 
CAREFUL: The score is not a direct measure of relevance, but it can be used as a rough guide.
Use your judgement to make sure the memory is really relevant to the user query.

# How do formulate your response
When responding to a request for memories, make sure your response is specific to the user request and 
does NOT contain any information that is not relevant to the user query.

Aggregate the relevant memories in a concise manner, no additional text or questions.
"""


@tool
def memorize(memories: List[Memory]):
    """Memorize information."""
    for memory in memories:
        insert_memory(memory.text, memory.category, Task.current())
    memories_markdown = "\n".join([f"- **{memory.category.replace('_', '')}** {memory.text}" for memory in memories])
    TaskEvent.add(actor="assistant", action="create_memories", message=memories_markdown)
    return "Memories created."


@tool
def retrieve_memories(prompt: str):
    """Retrieve memories. The search results' relevance is based on cosine similarity."""
    results = search_memories(prompt, Task.current(), top_k=5)
    if len(results) == 0:
        return "No Memories found."
    markdown = "Found memories. Not sure if they're 100% relevant - take them with a grain of salt:\n"
    for result in results:
        markdown += f"- **{result.memory.category.replace('_', '')}** {result.memory.text} (score: {result.score})\n"
    return markdown


@tool
def talk_to_memory_agent_agent(prompt: str):
    """Talk to the Memory agent."""
    github_agent = create_memory_agent()
    response = github_agent.invoke({"input": prompt})
    return response['output']



def create_memory_agent():
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, callbacks=[CostTrackerCallback("gpt-3.5-turbo", "memory agent")])
    tools = [retrieve_memories]

    prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate(prompt=PromptTemplate(input_variables=[], template=system_message)),
         HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
         MessagesPlaceholder(variable_name='agent_scratchpad')]
    )
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG)
