from typing import List

from langchain_core.prompts import ChatPromptTemplate

from core.documentation import Documentation
from core.event_log import EventLog
from engine.file_system import FileSystem
from engine.langchain.tools import BasicTool
from engine.util import get_logger

logger = logging.getLogger(__name__)

planner_system_prompt = """
You are a task execution planner.
Every task has:
- a natural-language description of what needs to be done
- An expected output
- Optional input data
 
You create a step-by-step plan for another LLM ("orchestrator"), who will be executing the task using the available tools. 
Your plan should be formatted as follows:

=== BEGIN PLAN ===

1. Use Tool <tool name> to <tool action>
2. Use Tool <tool name> to <tool action>
3. Use <information> to do <something>
...

The output is expected to be <expected output>
=== END PLAN ===


# Tools
Here is a list of tools and their parameters that you can use to create the plan:
{tools}

# Characteristics of a good plan

- **Short, clear and concise**: The plan should be easy to understand and follow.
- **Resourcefulness**: Some of the tools may be expensive (e.g. reading and analyzing flows) or slow (running code analyses). Take that into account when creating the plan.
- **True to the user's intent**: The plan should resemble the user's task description as closely as possible and NOT add any steps that aren't asked for
- **Project-specific**: Use the provided knowledge about the project to create a plan that is specific to the project.
- **Self-contained**: The plan should contain the necessary context information so that the orchestrator can execute it without needing to refer back

# Tool-specific RULES
Strictly follow these rules on how tool usage in your plan:

## Rule 1: NO Git-specific actions
Git-specific actions like commits, branches, merges, etc are not part of the plan.

## Rule 2: ONlY use Github-specific tools when asked
Tools for interacting with Github issues should only be part of the plan if the user's tool explicitly mentions them.

## Rule 3: Use Code Scanning ONLY when asked 
There are multiple tools for code scanning. Only use them if asked to do so by the user.

## Rule 4: Never Edit/Inspect more than FOUR FILES
These tools are EXPENSIVE. The plan must not mention or ask for editing/inspecting more than 4 distinct files.

## Rule 5: Be explicit with file names
The orchestrator has no knowledge of the file tree, so be explicit about the file names in the plan.

# Task Validation
You must ensure that the plans you create are executable using the tools available. In any of the following cases,
your plan should only say "Abort" and explain why:
- The plan asks for a tool that is not available
- The user didn't provide enough information to create a plan

"""


def build_planner(tools: List[BasicTool], llm):
    tool_descriptions = ""
    for tool in tools:
        schema = tool.openai_schema
        tool_descriptions += f"## `{schema['name']}`\n{schema['description']}\n"
        tool_parameters = ""
        for name, parameter in schema['parameters']['properties'].items():
            optional = name not in schema['parameters']['required']
            optional_str = "optional" if optional else "required"
            tool_parameters += f"- {name} ({optional_str}): {parameter['description']}\n"
        tool_descriptions += tool_parameters + "\n"
    instructions_template = """
    # Task Defined By User
    {task}
    
    # (Optional) Input Data Provided By User
    {input}
    
    # What we know about the project
    {knowledge_base}
    
    # File tree of the project
    {file_tree}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", planner_system_prompt),
        ("human", instructions_template),
        ("system", "Respond with the tool plan"),
    ]).partial(tools=tool_descriptions, knowledge_base=Documentation().project_facts, file_tree=FileSystem().yaml())
    return prompt | llm


def extract_plan(content: str) -> str:
    lines = content.split('\n')  # Split the content into lines
    inside_plan = False
    plan_content = []

    for line in lines:
        if line.strip().startswith('=== BEGIN PLAN ==='):
            inside_plan = True
        elif line.strip().startswith('=== END PLAN ==='):
            inside_plan = False
        elif inside_plan:
            plan_content.append(line)

    return '\n'.join(plan_content)

def planner_node_function(state, name, chain):
    result = chain.invoke(state)
    logger.info(f"Created plan:\n{result.content}")
    plan = extract_plan(result.content.strip())
    TaskEvent.add(actor="assistant", action="create_plan", message=plan)
    return {"plan": result.content}
