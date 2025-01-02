# graph_app.py

import logging
from typing import List
from typing_extensions import TypedDict

from langgraph.graph import START, END, StateGraph

# Import node functions
from gpt_interface2 import (
    scoping,
    retrieve,
    grade_documents,
    transform_query,
    handle_generic_response,
    generate,
    generate2,
    route_question,
    decide_to_generate,
    grade_generation_v_documents_and_question
)


###########################################################
# 11) Define our Graph State
###########################################################
class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    question: str
    generation: str
    documents: List[str]
    scope: str
    loopfix: bool


# Initialize the state with loopfix set to False
initial_state = GraphState(
    question="",
    generation="",
    documents=[],
    scope="",
    loopfix=False
)


###########################################################
# 12) Build the graph
###########################################################
def get_graph():
    """
    Build and compile the StateGraph for RAG pipeline.
    """
    if not hasattr(get_graph, 'app'):
        workflow = StateGraph(GraphState)

        # Add the nodes
        workflow.add_node("scoping", scoping)
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("transform_query", transform_query)
        workflow.add_node("handle_generic_response", handle_generic_response)
        workflow.add_node("generate", generate)
        workflow.add_node("generate2", generate2)

        # Build the graph with conditional logic
        workflow.add_conditional_edges(
            START,
            route_question,
            {
                "needs_context": "scoping",
                "generic": "handle_generic_response",
                "end": END,
            },
        )

        workflow.add_edge("scoping", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_edge("handle_generic_response", END)

        workflow.add_conditional_edges(
            "grade_documents",
            decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )

        # We keep track of how many times we've tried transform_query
        def check_transform_query(state):
            if 'loops' not in state:
                state['loops'] = 0
            if state['loops'] >= 3:
                return "generate2"
            else:
                state['loops'] += 1
                return "retrieve"

        workflow.add_conditional_edges(
            "transform_query",
            check_transform_query,
            {
                "generate2": "generate2",
                "retrieve": "retrieve"
            }
        )

        # Once generation is done, let's see if it is a good answer
        workflow.add_conditional_edges(
            "generate",
            grade_generation_v_documents_and_question,
            {
                "useful": END,
                "not useful": "transform_query",
            },
        )

        # The fallback generation node just ends
        workflow.add_edge("generate2", END)

        # Compile the workflow
        get_graph.app = workflow.compile()
    
    return get_graph.app