import json
import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from engine.langchain.tools import BasicTool

logger = logging.getLogger(__name__)

# Define special tools for orchestrato


@tool("abort_task", return_direct=False)
def abort_tool_tool(reason: str):
    """Abort the tool."""
    logger.info(f"Abort tool tool called")
    return {"aborted": True, "output": reason}


@tool("finish_task", return_direct=False)
def finish_tool_tool(output: str):
    """
    Finish the tool.

    :param output: A summary of the tool execution
    """
    logger.info(f"Finish tool tool called")
    return {"aborted": False, "output": output}

tools = BasicTool.all()
orchestrator_functions = [tool.openai_schema for tool in tools] + [abort_tool_tool, finish_tool_tool]
orchestrator_system_prompt = """
You are a task orchestrator. 
Every task has a natural-language description of what needs to be done, an expected output, and optional input data.
You will receive the following information:
- The task as described by the user
- A plan: Step-by-step instructions for executing the task
- Optional input data for the task
- A list of steps that have already been executed
You execute the plan step-by-step using the tools available to you.
Once you are done with the last step, call the "finish_task" tool with the expected output information.
If you need to abort the tool, call the "abort_task" tool and provide a reason for the abort.

# Guard rails
In order to save resources and improve performance, follow these guidelines:

# Never work on more than 4 files per task
`EditFiles` and `InespectFiles` are expensive. If the plan wants you to work on more than 4 files, 
pick 4 files that are most important and ignore the rest.

# Guidelines on how to formulate the output information
- If you changed files, mention the files that were changed and the changes that were made.
- No need to mention the names of the tools that you've used.
- Markdown-format the output
- When mentioning Github issues or PRs, always add Markdown links to the issues or PRs.
"""


def build_orchestrator(llm):
    instructions_template = """
    # Task Defined By User
    {task}
    
    Input data:
    {input}
    
    # Tool Execution Plan
    {plan}
    """

    model = llm.bind_functions(orchestrator_functions)
    prompt = ChatPromptTemplate.from_messages([
        ("system", orchestrator_system_prompt),
        ("human", instructions_template),
        MessagesPlaceholder(variable_name="steps_executed"),
        ("system", "Decide what to do next by calling one of your functions"),
    ]).partial()
    return prompt | model


def orchestrator_node_function(state, name, chain):
    """Run next step of the orchestrator"""
    if len(state["steps_executed"]) >= state["max_steps"]:
        logger.debug("Max steps reached")
        return {"aborted": True, "output": f"Tool aborted. Maximum number of steps reached: {state['max_steps']}"}
    result = chain.invoke(state)
    if "function_call" not in result.additional_kwargs:
        logger.warn("No function call detected in operator node, taking text output as is")
        return {"aborted": False, "output": result.content, "passed_review": True}
    tool_name = result.additional_kwargs["function_call"]["name"]
    try:
        tool_arguments = json.loads(result.additional_kwargs["function_call"]["arguments"])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse arguments for tool call: {tool_name}")
        return {"steps_executed": [f"Failed to parse arguments for tool call: {tool_name}"]}
    if tool_name == "finish_task":
        logger.info("Tool finished")
        return {"steps_executed": ["Tool finished"], "passed_review": True, "aborted": False, "output": tool_arguments["output"]}
    if tool_name == "abort_task":
        logger.info(f"Tool aborted: {tool_arguments['reason']}")
        return {"steps_executed": ["Tool aborted"], "passed_review": False, "aborted": True, "output": tool_arguments["reason"]}
    # Find the correct tool and run it
    logger.info(f"Handling tool call: {tool_name}")
    for basic_tool in BasicTool.all():
        if basic_tool.openai_schema['name'] == tool_name:
            executable = basic_tool.from_function_call(tool_arguments)
            try:
                result = f"{tool_name} returned:\n\n{executable.execute(state)}"
            except Exception as e:
                logger.error(f"Failed to execute tool {tool_name}", exc_info=e)
                result = f"Failed to execute tool {tool_name}: {e}"
            return {"steps_executed": [result]}
    return {"aborted": True, "output": f"No tool called {tool_name!r} found in the list of available tools."}
