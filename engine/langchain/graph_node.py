from typing import Any, TypedDict

from langchain_core.runnables import Runnable


class GraphNode:

    def __init__(self, name: str, chain: Runnable, node_function):
        self.name = name
        self.chain = chain
        self.node_function = node_function

    def call(self, state: TypedDict):
        return self.node_function(state, name=self.name, chain=self.chain)