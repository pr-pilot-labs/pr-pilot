import logging

logger = logging.getLogger(__name__)

AGENT_COMMUNICATION_RULES = """
# Communication Rules
When talking to the agents, you must follow these rules:
- Mention any relevant files/classes/functions/etc explicitly 
- Describe what you want them to do clearly
- Be specific about what you want their answer to look like
- Minimize the number of questions you ask the agents. Formulate fewer, combined requests when possible
"""