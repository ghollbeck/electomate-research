# # pipeline_functions.py

# import os
# import logging
# import dotenv
# from typing import List, Literal
# from typing_extensions import TypedDict
# from pydantic import BaseModel, Field

# from langchain.schema import Document
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnableConfig
# from langgraph.graph import START, END, StateGraph
# from langchain_openai import ChatOpenAI


# ######################
# # Llama Index Related
# ######################
# # We'll import from llama_index and set up the query engine
# from llama_index.core import StorageContext, load_index_from_storage


# ###########################################################
# # Helper function: get_llmTextNode
# ###########################################################
# def get_llm():
#     """
#     Returns a ChatOpenAI LLM. 
#     Adjust this to your preference, e.g., model="gpt-3.5-turbo" or "gpt-4" if you have access.
#     """
#     return ChatOpenAI(
#         model="gpt-4o",
#         temperature=0,
#     )


# ###########################################################
# # 1) Scoping
# ###########################################################
# def scoping(state):
#     """
#     Define the scope of the question.
    
#     Args:
#         state (dict): The current graph state

#     Returns:
#         dict: A new key added to the state, 'scope', that defines the scope of the query
#     """
#     logging.info("---SCOPE---")
#     question = state["question"]
    
#     class QueryScope(BaseModel):
#         """
#         Decide on the scope of the query.
#         If the question refers to the Constitution of Germany, use "constitution".
#         Else, use "all".
#         """
#         scope: Literal["constitution", "all"] = Field(
#             ...,
#             description="Given a user question choose to route it either to the Constitution of Germany or to all documents."
#         )

#     system = """You are an expert at deciding if a question refers to the constitution of Germany or requires general information. 
# If the question refers to the Constitution of Germany, use "constitution". 
# If the question refers to multiple topics, doesn't refer to the constitution specifically, or if you cannot decide, use "all". 
# Only answer with one of these two words: all OR constitution."""
    
#     route_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "Question: {question}"),
#         ]
#     )
    
#     question_router = route_prompt | get_llm().with_structured_output(QueryScope)
#     scope = question_router.invoke({"question": question})
    
#     return {"question": question, "scope": scope.scope}


# ###########################################################
# # 2) Retrieve
# ###########################################################
# def retrieve(state):
#     """
#     Retrieve documents based on the question (RAG approach).
#     """
#     logging.info("---RETRIEVE---")
#     question = state["question"]
#     scope = state["scope"]

#     # Load Llama Index
#     storage_context = StorageContext.from_defaults(persist_dir="index_store2")
#     index = load_index_from_storage(storage_context)

#     # Create a query engine with more comprehensive retrieval settings
#     query_engine = index.as_query_engine(
#         similarity_top_k=6,
#         response_mode="tree_summarize"
#     )

#     # Query the index
#     result = query_engine.query(question)

#     # Convert the retrieved source nodes into a list of Document objects
#     documents = []
#     if hasattr(result, 'source_nodes'):
#         for node in result.source_nodes:
#             # Handle both old and new node structures
#             doc_id = getattr(node.node, 'doc_id', None) or getattr(node.node, 'id_', None) or 'unknown'
#             documents.append(
#                 Document(
#                     page_content=node.node.text,
#                     metadata={"source": doc_id}
#                 )
#             )
    
#     return {"documents": documents, "scope": scope, "question": question}


# ###########################################################
# # 3) grade_documents
# ###########################################################
# def grade_documents(state):
#     """
#     Determines whether the retrieved documents are relevant to the question.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         dict: Updates 'documents' key with only filtered, relevant documents
#     """
#     logging.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
#     question = state["question"]
#     documents = state["documents"]
    
#     # We'll do a simple relevance check using a short prompt:
#     class GradeDocuments(BaseModel):
#         binary_score: str = Field(
#             description="Documents are relevant to the question, 'yes' or 'no'"
#         )

        
#     system = """You are a grader assessing relevance of a retrieved document to a user question. 
# If the document contains keyword(s) or semantic meaning related to the user question, grade it as 'yes'. Otherwise 'no'.
# """

#     grade_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "Retrieved document: \n\n {document} \n\nUser Question: {question}")
#         ]
#     )
#     retrieval_grader = grade_prompt | get_llm().with_structured_output(GradeDocuments)
        
#     # Score each doc
#     filtered_docs = []
#     for d in documents:
#         score = retrieval_grader.invoke(
#             {"question": question, "document": d.page_content}
#         )
#         grade = score.binary_score
#         if grade.strip().lower() == "yes":
#             logging.info("---GRADE: DOCUMENT RELEVANT---")
#             filtered_docs.append(d)
#         else:
#             logging.info("---GRADE: DOCUMENT NOT RELEVANT---")
#             continue

#     return {"documents": filtered_docs, "question": question, "scope": state["scope"]}


# ###########################################################
# # 4) transform_query
# ###########################################################
# def transform_query(state):
#     """
#     Transform the user query to produce a better (rephrased) question for retrieval.
#     """

#     logging.info("---TRANSFORM QUERY---")
#     question = state["question"]
#     documents = state["documents"]
    
#     system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval.
# Only output the new question. It should contain as many good keywords as possible for a retrieval-augmented generation pipeline.
# """

#     re_write_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "Question: Tell me more about the CDU in Germany?"),
#             ("assistant", "Explain the standpoints of the CDU in Germany generally."),
#             (
#                 "human",
#                 "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
#             ),
#         ]
#     )
#     question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
#     better_question = question_rewriter.invoke({"question": question})
#     return {"documents": documents, "question": better_question, "scope": state["scope"]}


# ###########################################################
# # 5) handle_generic_response
# ###########################################################
# def handle_generic_response(state):
#     """
#     Generate a generic response for simple questions that don't need context.
#     E.g., greetings or unrelated questions about the chatbot itself.
#     """

#     logging.info("---GENERATING GENERIC RESPONSE---")
#     question = state["question"]
    
#     system = """You are an AI assistant focused on helping users with questions about Germany's next elections. 
# For simple greetings or general questions about you, provide a friendly response while mentioning your main purpose. 
# You have access to official party manifestos and curated sources to help voters make informed decisions. 
# You are politically neutral and do not take sides. 
# You only answer questions about yourself in a generic manner. 
# You were developed by Students at ETH Zurich, Hochschule St. Gallen, and the University of Zurich. 
# You are running on the OpenAI API with the GPT-4o model.
# You cannot search the Web beyond your indexed documents.
# """
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", system),
#         ("human", "Hello"),
#         ("assistant", "Hey there, do you have any questions? I can help you browse through my sources like party manifestos and curated articles!"),
#         ("human", "Who are you?"),
#         ("assistant", "Hi! I'm an AI assistant aiming to help you with questions about the upcoming elections in Germany. I have a variety of internal documents to help me answer your queries."),
#         ("human", "{question}")
#     ])
    
#     chain = prompt | get_llm() | StrOutputParser()
#     generation = chain.invoke({"question": question})
    
#     return {
#         "question": question,
#         "generation": generation,
#         "documents": [],
#         "scope": "none"
#     }


# ###########################################################
# # 6) generate
# ###########################################################
# def generate(state):
#     """
#     Generate an answer from the retrieved documents (and general instructions).
#     """
#     logging.info("---GENERATE---")
#     question = state["question"]
#     documents = state["documents"]
#     scope = state["scope"]
    
#     system = """You are an expert assistant on Germany's political landscape and elections. 
# Use the provided context to answer questions accurately and concisely.
# If you don't know the answer, just say you don't know. 
# Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it.

# Key guidelines:
# 1. Base your answers primarily on the retrieved documents and general context
# 2. Be specific and factual
# 3. If information seems outdated or conflicts between sources, prioritize the most recent source
# 4. For policy questions, cite the specific party or document source
# 5. Always answer in English
# 6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
# 7. YOU ARE POLITICALLY NEUTRAL

# Information about you:
#   - You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
#   - You are running on the OpenAI API using the GPT-4o model.
#   - You cannot search the Web, but only retrieve information via a retrieval augmented generation pipeline from pre-indexed documents.

# Output format:
#   - If the output is long, first write a short line answer, then in a second paragraph elaborate more.
#   - Write your answer in Markdown format, with **bold** for keywords or names, and insert new lines for structure.
#   - After your answer, list the sources as "Source 1: (document name)", "Source 2: (document name)", etc.

# ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. 
# IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESN'T PROVIDE THE INFORMATION.
# """
    
#     rag_prompt = ChatPromptTemplate.from_messages([
#         ("system", system),
#         ("human", """Answer in Markdown format. 
# Question: {question}

# Please provide a clear and concise answer based on the above information.

# Retrieved Context:
# {context}
# """)
#     ])
    
#     # Convert the Document list into a text block
#     context_text = "\n\n".join([f"{i+1}. {doc.page_content[:300]}..." for i, doc in enumerate(documents)])
    
#     rag_chain = rag_prompt | get_llm() | StrOutputParser()
#     generation = rag_chain.invoke({"context": context_text, "question": question})
    
#     return {
#         "documents": [doc.page_content for doc in documents],
#         "scope": scope,
#         "question": question,
#         "generation": generation
#     }


# ###########################################################
# # 7) generate2
# ###########################################################
# def generate2(state):
#     """
#     Alternate generation approach with a slightly different system prompt.
#     Sometimes used as a fallback if transform_query can't find relevant docs.
#     """
#     logging.info("---GENERATE--- (Fallback generation 2)")
#     question = state["question"]
#     documents = state["documents"]
#     scope = state["scope"]
    
#     system = """You are an expert assistant on Germany's political landscape and elections. 
# Use the provided context to answer questions accurately and concisely.
# If you don't know the answer, just say that you don't know. 
# Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it.

# Key guidelines:
# 1. Base your answers primarily on the retrieved documents and general context
# 2. Be specific and factual
# 3. If information seems outdated or conflicts between sources, prioritize the most recent source
# 4. For policy questions, cite the specific party or document source
# 5. Always answer in English
# 6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
# 7. YOU ARE POLITICALLY NEUTRAL

# Information about you:
#   - You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
#   - You are running on the OpenAI API using the GPT-4o model.
#   - You cannot search the Web, but only retrieve information via a retrieval augmented generation pipeline from pre-indexed documents.

# Output format:
#   - If the output is long, first write a short line answer, then in a second paragraph elaborate more.
#   - Write your answer in Markdown format, with **bold** for keywords or names, and insert new lines for structure.
#   - After your answer, list the sources as "Source 1: (document name)", "Source 2: (document name)", etc.

# ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. 
# IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESN'T PROVIDE THE INFORMATION.
# """

#     rag_prompt = ChatPromptTemplate.from_messages([
#         ("system", system),
#         ("human", """Answer in Markdown format. 
# Question (the context might not contain the answer, so mention if you are uncertain about correctness): {question}

# Please provide a clear and concise answer based on the above information.

# Retrieved Context:
# {context}
# """)
#     ])

#     context_text = "\n\n".join([f"{i+1}. {doc.page_content[:300]}..." for i, doc in enumerate(documents)])
    
#     rag_chain = rag_prompt | get_llm() | StrOutputParser()
#     generation = rag_chain.invoke({"context": context_text, "question": question})
    
#     return {
#         "documents": [doc.page_content for doc in documents],
#         "scope": scope,
#         "question": question,
#         "generation": generation,
#         "loopfix": True
#     }


# ###########################################################
# # 8) route_question
# ###########################################################
# def route_question(state):
#     """
#     Decide if the question is relevant to Germany's election context or if it is a generic question.
#     """
#     logging.info("---ROUTE QUESTION---")
#     question = state["question"]
    
#     class RouteQuery(BaseModel):
#         decision: Literal["needs_context", "generic_response", "irrelevant"] = Field(
#             ...,
#             description="Determine how to handle the question: 'needs_context' for questions requiring Germany election info, 'generic_response' for simple/greeting questions, 'irrelevant' for unrelated questions."
#         )

#     system = """
# You are an expert at determining how to handle user questions about the next elections in Germany.

# Instructions:
# - If the question requires specific information about Germany's elections or politics, choose 'needs_context'
# - If the question is a simple greeting, or a question about you or your capabilities, or can be answered without specific German political knowledge, choose 'generic_response'
# - If the question is completely unrelated to Germany, choose 'irrelevant'
# """

#     route_prompt = ChatPromptTemplate.from_messages([
#         # Provide examples adapted to Germany
#         ("human", "Question: What are the main policies of the SPD?\nDecision:"),
#         ("assistant", "needs_context"),
#         ("human", "Question: Tell me about the weather in Argentina.\nDecision:"),
#         ("assistant", "irrelevant"),
#         ("human", "Question: Hey, how are you?\nDecision:"),
#         ("assistant", "generic_response"),
#         ("human", "Question: Who are you?\nDecision:"),
#         ("assistant", "generic_response"),
#         ("human", "Question: When is the next German election date?\nDecision:"),
#         ("assistant", "needs_context"),
#         ("human", "Question: Hello!\nDecision:"),
#         ("assistant", "generic_response"),
#         ("human", "Question: {question}\nDecision:"),
#     ])

#     question_router = route_prompt | get_llm().with_structured_output(RouteQuery)
#     source = question_router.invoke({"question": question})
#     logging.info(source)
    
#     if source.decision == "needs_context":
#         logging.info("---QUESTION NEEDS CONTEXT---")
#         return "needs_context"
#     elif source.decision == "generic_response":
#         logging.info("---GENERIC RESPONSE---")
#         return "generic"
#     else:
#         logging.info("---QUESTION IS IRRELEVANT---")
#         return "end"


# ###########################################################
# # 9) decide_to_generate
# ###########################################################
# def decide_to_generate(state):
#     """
#     Determines whether to generate an answer directly or re-generate the question if docs are absent.
#     """
#     logging.info("---ASSESS GRADED DOCUMENTS---")
#     filtered_documents = state["documents"]

#     if not filtered_documents:
#         # If no relevant documents remain, let's transform the query
#         logging.info("---DECISION: NO RELEVANT DOCS => TRANSFORM QUERY---")
#         return "transform_query"
#     else:
#         logging.info("---DECISION: GO AHEAD WITH GENERATE---")
#         return "generate"


# ###########################################################
# # 10) grade_generation_v_documents_and_question
# ###########################################################
# def grade_generation_v_documents_and_question(state):
#     """
#     Simple check to see if the answer addresses the question.
#     """

#     logging.info("---CHECK ANSWER AGAINST QUESTION---")
#     question = state["question"]
#     generation = state["generation"]

#     class GradeAnswer(BaseModel):
#         binary_score: str = Field(
#             description="Does the answer address the user's question? 'yes' or 'no'"
#         )

#     system = """You are a grader assessing whether an answer addresses the user's question about Germany. 
# Give a binary score 'yes' or 'no'. 'Yes' means the answer addresses or resolves the question sufficiently.
# """

#     answer_prompt = ChatPromptTemplate.from_messages([
#         ("system", system),
#         ("human", """User question: "Who was the Chancellor in 2021?" 
# LLM generation: "Angela Merkel was the Chancellor until December 2021, then Olaf Scholz took over."
# Answer Relevance: """),
#         ("assistant", "yes"),
#         ("human", "User question: {question}\nLLM generation: {generation}")
#     ])
    
#     answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)
#     score = answer_grader.invoke({"question": question, "generation": generation})
#     grade = score.binary_score

#     if grade == "yes":
#         logging.info("---DECISION: GENERATION ADDRESSES QUESTION---")
#         return "useful"
#     else:
#         logging.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
#         return "not useful"


# ###########################################################
# # 11) Define our Graph State
# ###########################################################
# class GraphState(TypedDict):
#     """
#     Represents the state of our graph.
#     """
#     question: str
#     generation: str
#     documents: List[str]
#     scope: str
#     loopfix: bool

# # Initialize the state with loopfix set to False
# initial_state = GraphState(
#     question="",
#     generation="",
#     documents=[],
#     scope="",
#     loopfix=False
# )


# ###########################################################
# # 12) Build the graph
# ###########################################################
# def get_graph():
#     """
#     Build and compile the StateGraph for RAG pipeline.
#     """
#     if not hasattr(get_graph, 'app'):
#         workflow = StateGraph(GraphState)

#         # Add the nodes
#         workflow.add_node("scoping", scoping)
#         workflow.add_node("retrieve", retrieve)
#         workflow.add_node("grade_documents", grade_documents)
#         workflow.add_node("transform_query", transform_query)
#         workflow.add_node("handle_generic_response", handle_generic_response)
#         workflow.add_node("generate", generate)
#         workflow.add_node("generate2", generate2)

#         # Build the graph with conditional logic
#         workflow.add_conditional_edges(
#             START,
#             route_question,
#             {
#                 "needs_context": "scoping",
#                 "generic": "handle_generic_response",
#                 "end": END,
#             },
#         )

#         workflow.add_edge("scoping", "retrieve")
#         workflow.add_edge("retrieve", "grade_documents")
#         workflow.add_edge("handle_generic_response", END)

#         workflow.add_conditional_edges(
#             "grade_documents",
#             decide_to_generate,
#             {
#                 "transform_query": "transform_query",
#                 "generate": "generate",
#             },
#         )

#         # We keep track of how many times we've tried transform_query
#         def check_transform_query(state):
#             if 'loops' not in state:
#                 state['loops'] = 0
#             if state['loops'] >= 3:
#                 return "generate2"
#             else:
#                 state['loops'] += 1
#                 return "retrieve"

#         workflow.add_conditional_edges(
#             "transform_query",
#             check_transform_query,
#             {
#                 "generate2": "generate2",
#                 "retrieve": "retrieve"
#             }
#         )

#         # Once generation is done, let's see if it is a good answer
#         workflow.add_conditional_edges(
#             "generate",
#             grade_generation_v_documents_and_question,
#             {
#                 "useful": END,
#                 "not useful": "transform_query",
#             },
#         )

#         # The fallback generation node just ends
#         workflow.add_edge("generate2", END)

#         # Compile
#         get_graph.app = workflow.compile()
    
#     return get_graph.app




# pipeline_functions.py

import logging
from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

######################
# Llama Index Related
######################
from llama_index.core import StorageContext, load_index_from_storage


###########################################################
# Helper function: get_llm
###########################################################
def get_llm():
    """
    Returns a ChatOpenAI LLM. 
    Adjust this to your preference, e.g., model="gpt-3.5-turbo" or "gpt-4" if you have access.
    """
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
    )


###########################################################
# 1) Scoping
###########################################################
def scoping(state):
    """
    Define the scope of the question.
    
    Args:
        state (dict): The current graph state

    Returns:
        dict: A new key added to the state, 'scope', that defines the scope of the query
    """
    logging.info("---SCOPE---")
    question = state["question"]
    
    class QueryScope(BaseModel):
        """
        Decide on the scope of the query.
        If the question refers to the Constitution of Germany, use "constitution".
        Else, use "all".
        """
        scope: Literal["constitution", "all"] = Field(
            ...,
            description="Given a user question choose to route it either to the Constitution of Germany or to all documents."
        )

    system = """You are an expert at deciding if a question refers to the constitution of Germany or requires general information. 
If the question refers to the Constitution of Germany, use "constitution". 
If the question refers to multiple topics, doesn't refer to the constitution specifically, or if you cannot decide, use "all". 
Only answer with one of these two words: all OR constitution."""
    
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Question: {question}"),
        ]
    )
    
    question_router = route_prompt | get_llm().with_structured_output(QueryScope)
    scope = question_router.invoke({"question": question})
    
    return {"question": question, "scope": scope.scope}


###########################################################
# 2) Retrieve
###########################################################
def retrieve(state):
    """
    Retrieve documents based on the question (RAG approach).
    """
    logging.info("---RETRIEVE---")
    question = state["question"]
    scope = state["scope"]

    # Load Llama Index
    storage_context = StorageContext.from_defaults(persist_dir="index_store2")
    index = load_index_from_storage(storage_context)

    # Create a query engine with more comprehensive retrieval settings
    query_engine = index.as_query_engine(
        similarity_top_k=6,
        response_mode="tree_summarize"
    )

    # Query the index
    result = query_engine.query(question)

    # Convert the retrieved source nodes into a list of Document objects
    documents = []
    if hasattr(result, 'source_nodes'):
        for node in result.source_nodes:
            # Handle both old and new node structures
            doc_id = getattr(node.node, 'doc_id', None) or getattr(node.node, 'id_', None) or 'unknown'
            documents.append(
                Document(
                    page_content=node.node.text,
                    metadata={"source": doc_id}
                )
            )
    
    return {"documents": documents, "scope": scope, "question": question}


###########################################################
# 3) grade_documents
###########################################################
def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        dict: Updates 'documents' key with only filtered, relevant documents
    """
    logging.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    class GradeDocuments(BaseModel):
        binary_score: str = Field(
            description="Documents are relevant to the question, 'yes' or 'no'"
        )

    system = """You are a grader assessing relevance of a retrieved document to a user question. 
If the document contains keyword(s) or semantic meaning related to the user question, grade it as 'yes'. Otherwise 'no'.
"""

    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Retrieved document: \n\n {document} \n\nUser Question: {question}")
        ]
    )
    retrieval_grader = grade_prompt | get_llm().with_structured_output(GradeDocuments)
        
    # Score each doc
    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score.binary_score
        if grade.strip().lower() == "yes":
            logging.info("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            logging.info("---GRADE: DOCUMENT NOT RELEVANT---")
            continue

    return {"documents": filtered_docs, "question": question, "scope": state["scope"]}


###########################################################
# 4) transform_query
###########################################################
def transform_query(state):
    """
    Transform the user query to produce a better (rephrased) question for retrieval.
    """

    logging.info("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    
    system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval.
Only output the new question. It should contain as many good keywords as possible for a retrieval-augmented generation pipeline.
"""

    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Question: Tell me more about the CDU in Germany?"),
            ("assistant", "Explain the standpoints of the CDU in Germany generally."),
            (
                "human",
                "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
            ),
        ]
    )
    question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question, "scope": state["scope"]}


###########################################################
# 5) handle_generic_response
###########################################################
def handle_generic_response(state):
    """
    Generate a generic response for simple questions that don't need context.
    E.g., greetings or unrelated questions about the chatbot itself.
    """

    logging.info("---GENERATING GENERIC RESPONSE---")
    question = state["question"]
    
    system = """You are an AI assistant focused on helping users with questions about Germany's next elections. 
For simple greetings or general questions about you, provide a friendly response while mentioning your main purpose. 
You have access to official party manifestos and curated sources to help voters make informed decisions. 
You are politically neutral and do not take sides. 
You only answer questions about yourself in a generic manner. 
You were developed by Students at ETH Zurich, Hochschule St. Gallen, and the University of Zurich. 
You are running on the OpenAI API with the GPT-4o model.
You cannot search the Web beyond your indexed documents.
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "Hello"),
        ("assistant", "Hey there, do you have any questions? I can help you browse through my sources like party manifestos and curated articles!"),
        ("human", "Who are you?"),
        ("assistant", "Hi! I'm an AI assistant aiming to help you with questions about the upcoming elections in Germany. I have a variety of internal documents to help me answer your queries."),
        ("human", "{question}")
    ])
    
    chain = prompt | get_llm() | StrOutputParser()
    generation = chain.invoke({"question": question})
    
    return {
        "question": question,
        "generation": generation,
        "documents": [],
        "scope": "none"
    }


###########################################################
# 6) generate
###########################################################
def generate(state):
    """
    Generate an answer from the retrieved documents (and general instructions).
    """
    logging.info("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    scope = state["scope"]
    
    system = """You are an expert assistant on Germany's political landscape and elections. 
Use the provided context to answer questions accurately and concisely.
If you don't know the answer, just say you don't know. 
Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it.

Key guidelines:
1. Base your answers primarily on the retrieved documents and general context
2. Be specific and factual
3. If information seems outdated or conflicts between sources, prioritize the most recent source
4. For policy questions, cite the specific party or document source
5. Always answer in English
6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
7. YOU ARE POLITICALLY NEUTRAL

Information about you:
  - You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
  - You are running on the OpenAI API using the GPT-4o model.
  - You cannot search the Web, but only retrieve information via a retrieval augmented generation pipeline from pre-indexed documents.

Output format:
  - If the output is long, first write a short line answer, then in a second paragraph elaborate more.
  - Write your answer in Markdown format, with **bold** for keywords or names, and insert new lines for structure.
  - After your answer, list the sources as "Source 1: (document name)", "Source 2: (document name)", etc.

ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. 
IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESN'T PROVIDE THE INFORMATION.
"""
    
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", """Answer in Markdown format. 
Question: {question}

Please provide a clear and concise answer based on the above information.

Retrieved Context:
{context}
""")
    ])
    
    context_text = "\n\n".join([f"{i+1}. {doc.page_content[:300]}..." for i, doc in enumerate(documents)])
    
    rag_chain = rag_prompt | get_llm() | StrOutputParser()
    generation = rag_chain.invoke({"context": context_text, "question": question})
    
    return {
        "documents": [doc.page_content for doc in documents],
        "scope": scope,
        "question": question,
        "generation": generation
    }


###########################################################
# 7) generate2
###########################################################
def generate2(state):
    """
    Alternate generation approach with a slightly different system prompt.
    Sometimes used as a fallback if transform_query can't find relevant docs.
    """
    logging.info("---GENERATE--- (Fallback generation 2)")
    question = state["question"]
    documents = state["documents"]
    scope = state["scope"]
    
    system = """You are an expert assistant on Germany's political landscape and elections. 
Use the provided context to answer questions accurately and concisely.
If you don't know the answer, just say that you don't know. 
Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it.

Key guidelines:
1. Base your answers primarily on the retrieved documents and general context
2. Be specific and factual
3. If information seems outdated or conflicts between sources, prioritize the most recent source
4. For policy questions, cite the specific party or document source
5. Always answer in English
6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
7. YOU ARE POLITICALLY NEUTRAL

Information about you:
  - You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
  - You are running on the OpenAI API using the GPT-4o model.
  - You cannot search the Web, but only retrieve information via a retrieval augmented generation pipeline from pre-indexed documents.

Output format:
  - If the output is long, first write a short line answer, then in a second paragraph elaborate more.
  - Write your answer in Markdown format, with **bold** for keywords or names, and insert new lines for structure.
  - After your answer, list the sources as "Source 1: (document name)", "Source 2: (document name)", etc.

ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. 
IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESN'T PROVIDE THE INFORMATION.
"""

    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", """Answer in Markdown format. 
Question (the context might not contain the answer, so mention if you are uncertain about correctness): {question}

Please provide a clear and concise answer based on the above information.

Retrieved Context:
{context}
""")
    ])

    context_text = "\n\n".join([f"{i+1}. {doc.page_content[:300]}..." for i, doc in enumerate(documents)])
    
    rag_chain = rag_prompt | get_llm() | StrOutputParser()
    generation = rag_chain.invoke({"context": context_text, "question": question})
    
    return {
        "documents": [doc.page_content for doc in documents],
        "scope": scope,
        "question": question,
        "generation": generation,
        "loopfix": True
    }


###########################################################
# 8) route_question
###########################################################
def route_question(state):
    """
    Decide if the question is relevant to Germany's election context or if it is a generic question.
    """
    logging.info("---ROUTE QUESTION---")
    question = state["question"]
    
    class RouteQuery(BaseModel):
        decision: Literal["needs_context", "generic_response", "irrelevant"] = Field(
            ...,
            description="Determine how to handle the question: 'needs_context' for questions requiring Germany election info, 'generic_response' for simple/greeting questions, 'irrelevant' for unrelated questions."
        )

    system = """
You are an expert at determining how to handle user questions about the next elections in Germany.

Instructions:
- If the question requires specific information about Germany's elections or politics, choose 'needs_context'
- If the question is a simple greeting, or a question about you or your capabilities, or can be answered without specific German political knowledge, choose 'generic_response'
- If the question is completely unrelated to Germany, choose 'irrelevant'
"""

    route_prompt = ChatPromptTemplate.from_messages([
        ("human", "Question: What are the main policies of the SPD?\nDecision:"),
        ("assistant", "needs_context"),
        ("human", "Question: Tell me about the weather in Argentina.\nDecision:"),
        ("assistant", "irrelevant"),
        ("human", "Question: Hey, how are you?\nDecision:"),
        ("assistant", "generic_response"),
        ("human", "Question: Who are you?\nDecision:"),
        ("assistant", "generic_response"),
        ("human", "Question: When is the next German election date?\nDecision:"),
        ("assistant", "needs_context"),
        ("human", "Question: Hello!\nDecision:"),
        ("assistant", "generic_response"),
        ("human", "Question: {question}\nDecision:"),
    ])

    question_router = route_prompt | get_llm().with_structured_output(RouteQuery)
    source = question_router.invoke({"question": question})
    logging.info(source)
    
    if source.decision == "needs_context":
        logging.info("---QUESTION NEEDS CONTEXT---")
        return "needs_context"
    elif source.decision == "generic_response":
        logging.info("---GENERIC RESPONSE---")
        return "generic"
    else:
        logging.info("---QUESTION IS IRRELEVANT---")
        return "end"


###########################################################
# 9) decide_to_generate
###########################################################
def decide_to_generate(state):
    """
    Determines whether to generate an answer directly or re-generate the question if docs are absent.
    """
    logging.info("---ASSESS GRADED DOCUMENTS---")
    filtered_documents = state["documents"]

    if not filtered_documents:
        # If no relevant documents remain, let's transform the query
        logging.info("---DECISION: NO RELEVANT DOCS => TRANSFORM QUERY---")
        return "transform_query"
    else:
        logging.info("---DECISION: GO AHEAD WITH GENERATE---")
        return "generate"


###########################################################
# 10) grade_generation_v_documents_and_question
###########################################################
def grade_generation_v_documents_and_question(state):
    """
    Simple check to see if the answer addresses the question.
    """

    logging.info("---CHECK ANSWER AGAINST QUESTION---")
    question = state["question"]
    generation = state["generation"]

    class GradeAnswer(BaseModel):
        binary_score: str = Field(
            description="Does the answer address the user's question? 'yes' or 'no'"
        )

    system = """You are a grader assessing whether an answer addresses the user's question about Germany. 
Give a binary score 'yes' or 'no'. 'Yes' means the answer addresses or resolves the question sufficiently.
"""

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", """User question: "Who was the Chancellor in 2021?" 
LLM generation: "Angela Merkel was the Chancellor until December 2021, then Olaf Scholz took over."
Answer Relevance: """),
        ("assistant", "yes"),
        ("human", "User question: {question}\nLLM generation: {generation}")
    ])
    
    answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)
    score = answer_grader.invoke({"question": question, "generation": generation})
    grade = score.binary_score

    if grade == "yes":
        logging.info("---DECISION: GENERATION ADDRESSES QUESTION---")
        return "useful"
    else:
        logging.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
        return "not useful"