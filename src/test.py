

import os

from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langchain_community.retrievers import AzureAISearchRetriever
from langchain_openai import ChatOpenAI


from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

import logging
import dotenv

def get_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
    )








def scoping(state):
    """
    Define the scope of the question
    
    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, scope, that defines the scope of the query
    """
    logging.info("---SCOPE---")
    question = state["question"]
    
    class QueryScope(BaseModel):
        """Decide on the scope of the query."""
        


        # "movementforchange", "ndc", "npp", "thenewforce",
        scope: Literal["constitution", "all"] = Field(
            ...,
            description="Given a user question choose to route it either to specific party in the Ghana 2024 elections, either to the constitution or just to look through all the documents.",
        )
    system = """You are an expert at deciding if a question refers to the constitution of Ghana or requires general information. 
    If the question refers to the Constitution of Ghana, use "constitution". If the question refers to multiple topics, 
    doesn't refer to the constitution specifically, or if you cannot decide, use "all". Only answer with one of these two words: all OR constitution\n """
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Question: {question}")
        ]
    )
    question_router = route_prompt | get_llm().with_structured_output(QueryScope)
    
    scope = question_router.invoke({"question": question})
    return {"question": question, "scope": scope.scope}








def retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    logging.info("---RETRIEVE---")
    question = state["question"]
    scope = state["scope"].lower()
    
    # ensure retriever is define
    retriever = AzureAISearchRetriever(
        api_version="2024-07-01",
        content_key="chunk",
        top_k=7
    )
        
    # Set Filter
    if scope == "constitution":
        retriever.filter = "title eq 'constitution.pdf'"
    elif scope == "npp":
        retriever.filter = "title eq 'npp.pdf'"
    elif scope == "ndc":
        retriever.filter = "title eq 'ndc.pdf'"
    elif scope == "movementforchange":
        retriever.filter = "title eq 'movementforchange.pdf'"
    elif scope == "thenewforce":
        retriever.filter = "title eq 'thenewforce.pdf'"
    else:
        retriever.filter = None

    # Retrieval
    documents = retriever.invoke(question)
    return {"documents": documents, "scope": scope, "question": question}










def generate(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    logging.info("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    scope = state["scope"]
    
#     # Ensure RAG chain is built
    system = """You are an expert assistant on Ghana's political landscape and elections. 
    Use the provided context to answer questions accurately and concisely.
      If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it specifically.

Key guidelines:
1. Base your answers primarily on the retrieved documents and general context
2. Be specific and factual
3. If information seems outdated or conflicts between sources, prioritize the most recent source
4. For policy questions, cite the specific party or document source
5. Alays answe in english
6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
7. YOU ARE POLITICALLY NEUTRAL


Information about you: 
     You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
     You are running on the OpenAI API using the GPT-4o model.
     You can't search the Web, but only retrive information via a retrieval augemnted generaion pipline form pre-indexed documents.


     Outputformat: make it structure in a way that its readable for the user. If the output is long, first write one short line answer and then in a second paragraph you elaborate more. BUT DONT MAKE HEADLINES.
     first write your answer in markdown format with key words or key names written in bold. Insert new lines for struture. Insert a new line after your answer.
     Source 1: (just write the name of the document)
     Source 2 (if applicable): (just write the name of the document)
     Source 3 (if applicable): (just write the name of the document)
     Source ... (if applicable): (just write the name of the document)




ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESNT PROVIDE THE INFORMATION.



"""


    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system),

         
    ("human", "Question: Who was the president in 2021?:"),
    ("assistant", """**Nana Akufo-Addo** served as President of Ghana in 2021. \n

He won re-election in December 2020 with **51.3%** of the vote and continued his presidency after the Supreme Court dismissed election challenges.

Source 1: Ghana_ Freedom in the World 2023 Country Report.pdf
Source 2: System prompt"""),


    
        ("human", """Answer in Markdown format. Question: {question}

Please provide a clear and concise answer based on the above information.
Retrieved Context:
{context}


""")
    ])

    rag_chain = rag_prompt | get_llm() | StrOutputParser()
        

    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": [document.page_content for document in documents], "scope": scope, "question": question, "generation": generation}










def generate2(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    logging.info("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    scope = state["scope"]
    
#     # Ensure RAG chain is built
    system = """You are an expert assistant on Ghana's political landscape and elections. 
    Use the provided context to answer questions accurately and concisely.
      If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer focused, only make longer statements if the user asks for it specifically.

Key guidelines:
1. Base your answers primarily on the retrieved documents and general context
2. Be specific and factual
3. If information seems outdated or conflicts between sources, prioritize the most recent source
4. For policy questions, cite the specific party or document source
5. Alays answe in english
6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
7. YOU ARE POLITICALLY NEUTRAL


Information about you: 
     You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
     You are running on the OpenAI API using the GPT-4o model.
     You can't search the Web, but only retrive information via a retrieval augemnted generaion pipline form pre-indexed documents.


     Outputformat: make it structure in a way that its readable for the user. If the output is long, first write one short line answer and then in a second paragraph you elaborate more. BUT DONT MAKE HEADLINES.
     first write your answer in markdown format with key words or key names written in bold. Insert new lines for struture. Insert a new line after your answer.
     Source 1: (just write the name of the document)
     Source 2 (if applicable): (just write the name of the document)
     Source 3 (if applicable): (just write the name of the document)
     Source ... (if applicable): (just write the name of the document)




These is a General Election Context, only use as context for your self and do not overload the user with too many numbers, only dump them with the detailed information if the user asks for specificities:

# GHANA ELECTIONS AND POLITICAL LANDSCAPE
Last Updated: 2023-10-01

## 1. ELECTORAL SYSTEM OVERVIEW

### Electoral Framework

- **Government Type**: Constitutional democracy with multi-party system.
- **Executive**: President elected for a four-year term; maximum of two terms.
- **Legislature**: Unicameral Parliament with 275 seats.
- **Electoral System**:
  - **Presidential**: Simple majority.
  - **Parliamentary**: First-past-the-post in single-member constituencies.
- **Electoral Body**: Independent Electoral Commission (EC) of Ghana.

### Voter Eligibility

- **Age**: 18 years and above.
- **Citizenship**: Ghanaian.
- **Residency**: Resident in registering constituency.
- **Disqualifications**: Unsound mind or certain convictions.

### Registration Process

- **Continuous Registration**: At district offices.
- **Biometric Data**: Fingerprints and photos to prevent duplicates.
- **Required Documents**:
  - National ID card.
  - Passport.

### Voting Procedures

- **Method**: Manual paper ballots.
- **Locations**: Schools, community centers, public buildings.
- **Hours**: 7:00 AM to 5:00 PM.
- **Identification**: Voter ID card required.

### Electoral Calendar

- **Election Cycle**: Every four years.
- **Next Election**: 2024-12-07.
- **Key Dates**:
  - **Nominations**: Two months before election day.
  - **Campaign Period**: Ends 24 hours before election day.

### Constituencies

- **Total**: 275 single-member constituencies.
- **Boundary Reviews**: Periodic updates by the EC.

## 2. POLITICAL PARTIES

### Major Parties

#### New Patriotic Party (NPP)

- **Leadership**:
  - **Chairman**: Freddie Blay.
  - **General Secretary**: John Boadu.
- **Key Figures**:
  - **Nana Akufo-Addo**: President since 2017.
  - **Dr. Mahamudu Bawumia**: Vice President.
- **Ideology**: Liberal democracy, free-market principles.
- **Achievements**:
  - Free Senior High School policy.
  - "One District, One Factory" program.
- **Recent Performance**:
  - **2016**: Won presidency and parliamentary majority.
  - **2020**: Retained presidency; slim parliamentary majority.

#### National Democratic Congress (NDC)

- **Leadership**:
  - **Chairman**: Samuel Ofosu-Ampofo.
  - **General Secretary**: Johnson Asiedu Nketia.
- **Key Figures**:
  - **John Mahama**: Former President (2012-2017).
- **Ideology**: Social democracy, inclusive governance.
- **Achievements**:
  - Infrastructure expansion.
  - National Health Insurance Scheme.
- **Recent Performance**:
  - **2012**: Won presidency and majority.
  - **2020**: Narrow losses in presidency and Parliament.

## 3. POLITICAL TIMELINE

### Governments Since Independence

| Period        | Leader                     | Government Type         |
|---------------|----------------------------|-------------------------|
| 1957-1966     | Kwame Nkrumah              | First Republic (CPP)    |
| 1966-1969     | Military Junta             | National Liberation     |
| 1969-1972     | Kofi Abrefa Busia          | Second Republic         |
| 1981-1992     | Jerry John Rawlings        | PNDC Military Govt.     |
| 1992-Present  | Multiple Leaders           | Fourth Republic         |

### Major Events

- **1966-02-24**: Nkrumah's government overthrown.
- **1981-12-31**: Rawlings establishes PNDC.
- **1992**: Return to constitutional rule.

### Recent Election Results

- **2020 Presidential**:
  - **NPP**: Nana Akufo-Addo - 51.3%.
  - **NDC**: John Mahama - 47.4%.
- **Parliament**:
  - **NPP**: 137 seats.
  - **NDC**: 137 seats.

### Government Structure

- **Presidential Term Limit**: Two four-year terms.
- **Parliamentary Terms**: Four years, no term limits.
- **Branches**:
  - **Executive**: President and ministers.
  - **Legislature**: Unicameral Parliament.
  - **Judiciary**: Independent Supreme Court.

## 4. CURRENT POLITICAL LANDSCAPE

### Key Figures

- **President**: Nana Akufo-Addo (NPP).
- **Vice President**: Dr. Mahamudu Bawumia.
- **Opposition Leader**: John Mahama (NDC).
- **Speaker of Parliament**: Alban Bagbin (NDC).

### Parliamentary Composition

- **Total Seats**: 275.
- **NPP**: 137 seats.
- **NDC**: 137 seats.
- **Independent**: 1 seat (aligns with NPP).

## 5. ECONOMIC INDICATORS

### GDP Growth (Past 5 Years)

| Year | Growth Rate (%) |
|------|-----------------|
| 2017 | 8.1             |
| 2018 | 6.3             |
| 2019 | 6.5             |
| 2020 | 0.9             |
| 2021 | 5.4             |

### Inflation Rates

- **2020**: 9.9%.
- **2021**: 9.8%.
- **2022**: Increased due to global factors.

### Economic Challenges

- **Debt**: Public debt at ~76.6% of GDP (2021).
- **Fiscal Deficit**: Expanded due to COVID-19.
- **Currency**: Depreciation of the Ghanaian Cedi.
- **Unemployment**: High youth unemployment rates.

### Key Sectors

- **Agriculture**: Cocoa, timber.
- **Mining**: Gold, oil.
- **Services**: Banking, tourism.
- **Manufacturing**: Emerging sector.

### Foreign Investment

- **FDI Inflows (2020)**: ~$2.65 billion.
- **Major Investors**: China, UK, USA.

## 6. POLICY CHALLENGES

### National Issues

1. **Economic Stability**: Inflation and debt management.
2. **Employment**: Youth job creation.
3. **Healthcare**: Infrastructure and access.
4. **Education**: Quality and resources.
5. **Infrastructure**: Roads, energy, digitalization.

### Infrastructure Status

- **Roads**: Ongoing improvements.
- **Energy**: Increased capacity; stability issues.
- **Digital**: National addressing system implemented.

### Education and Healthcare

- **Education**:
  - Free Senior High School since 2017.
  - Challenges: Overcrowding, teacher training.
- **Healthcare**:
  - National Health Insurance Scheme.
  - Issues: Funding, rural access.

### Environmental Concerns

- **Illegal Mining**: Water pollution.
- **Deforestation**: From logging and farming.
- **Climate Change**: Affects agriculture.

## 7. FOREIGN RELATIONS

### International Partnerships

- **ECOWAS**: Active member.
- **African Union**: Founding member.
- **United Nations**: Peacekeeping contributions.

### Regional Role

- **Diplomacy**: Mediator in conflicts.
- **Trade**: Promotes intra-African trade.
- **AfCFTA**: Hosts the Secretariat.

### Trade Agreements

- **AfCFTA**: Continental free trade.
- **EU Agreement**: Interim Economic Partnership.

### Diplomatic Missions

- **Global Embassies**: Extensive network.
- **Foreign Missions**: Over 60 in Ghana.

## 8. VOTING PROCESS

### Procedure Steps

1. **Arrival**: At assigned polling station.
2. **Verification**: Present Voter ID.
3. **Biometric Check**: Fingerprint scan.
4. **Ballot Issuance**: Receive ballots.
5. **Voting**: Mark choices privately.
6. **Casting**: Deposit ballots.
7. **Ink Marking**: Finger marked.
8. **Departure**: Exit polling station.

### Required Documentation

- **Voter ID Card**: Primary ID.
- **Alternate ID**: National ID or passport (if accepted).

### Polling Operations

- **Staff**: Presiding officer and assistants.
- **Observers**: Party agents, accredited monitors.
- **Security**: Police presence.

### Vote Counting

- **On-site Counting**: Immediate after polls close.
- **Transparency**: Open to observers.
- **Result Transmission**: Sent to constituency centers.

### Results Announcement

- **Collation**: Constituency and national levels.
- **Declaration**: By EC Chairperson.
- **Timeframe**: Within 72 hours.

---

**Note**: Information is accurate as of 2023-10-01. For updates, refer to official sources like the Electoral Commission of Ghana.

[End of general information]

ONLY USE THE ABOVE INFORMATION AND THE PROVIDED CONTEXT FOR YOUR ANSWER. IF YOU CANNOT ANSWER THE QUESTION WITH THE AVAILABLE INFORMATION, SAY THAT YOU DO NOT KNOW BECAUSE THE CONTEXT DOESNT PROVIDE THE INFORMATION.




"""


    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system),

         
    ("human", "Question (the context might not contain the answer, so so answer as good as you can and mention if you are uncertain about the answers correctness): Who was the president in 2021?:"),
    ("assistant", """**Nana Akufo-Addo** served as President of Ghana in 2021. \n

Based on limited context I think he won re-election in December 2020 with **51.3%** of the vote and continued his presidency after the Supreme Court dismissed election challenges. 

Source 1: Ghana_ Freedom in the World 2023 Country Report.pdf
Source 2: System prompt"""),


    
        ("human", """Answer in Markdown format. Question (the context might not contain the answer, so so answer as good as you can and mention if you are uncertain about the answers correctness): {question}

Please provide a clear and concise answer based on the above information.
Retrieved Context:
{context}


""")
    ])

    rag_chain = rag_prompt | get_llm() | StrOutputParser()
        

    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": [document.page_content for document in documents], "scope": scope, "question": question, "generation": generation, "loopfix":True}













def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """

    logging.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    # Ensure grader is built
    class GradeDocuments(BaseModel):
        """Binary score for relevance check on retrieved documents."""

        binary_score: str = Field(
            description="Documents are relevant to the question, 'yes' or 'no'"
        )
    system = """You are a grader assessing relevance of a retrieved document to a user question. If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. It does not need to be a stringent test. The goal is to filter out erroneous retrievals. Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Retrieved document: \n\n {document} \n\nUser Question: {question}"),
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
        if grade == "yes":
            logging.info("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            logging.info("---GRADE: DOCUMENT NOT RELEVANT---")
            continue
    return {"documents": filtered_docs, "question": question}


def transform_query(state):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """

    logging.info("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    
    # Ensure that question re-writer is built
    system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval. 
    Look at the input and try to reason about the underlying semantic intent / meaning. Only output the new question. 
    It should contain as good keywords as possible for the retrieval augentemnted generation as possible.


    
    """




    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),


            ("human", "Question: Tell me more about the New Patriotic Party?:"),
            ("assistant", "explain the standpoints of new patriotic party in ghana generally"),
     

            (
                "human",
                "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
            )
        ]
    )
    question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}

### Edges ###

def route_question(state):
    """
    Decide if the question is relevant and if it needs context.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """
    logging.info("---ROUTE QUESTION---")
    question = state["question"]
    
    class RouteQuery(BaseModel):
        """Route a user query to the most relevant path."""
        
        decision: Literal["needs_context", "generic_response", "irrelevant"] = Field(
            ...,
            description="Determine how to handle the question: 'needs_context' for questions requiring Ghana elections info, 'generic_response' for simple/greeting questions, 'irrelevant' for unrelated questions.",
        )

    system = """
You are an expert at determining how to handle user questions about the 2024 Ghana elections.

Instructions:
- If the question requires specific information about Ghana elections or politics (expect the user to ask within the context of the ghana elections, even if its not clear of which country the user is asking about): choose 'needs_context'
- If the question is a simple greeting, a question about you or your capabilities or a question that can be answered without specific Ghana knowledge: choose 'generic_response'
- If the question is completely unrelated to Ghana: choose 'irrelevant'

Examples:
1. Question: "What are the main policies of the New Patriotic Party?"
   Decision: needs_context

2. Question: "Tell me about the weather in Canada."
   Decision: irrelevant

3. Question: "Hey, how are you?"
   Decision: generic_response

4. Question: "Hi, what can you help me with?"
   Decision: generic_response

5. Question: "When is the 2024 election date?"
   Decision: needs_context

6. Question: "rgasdgfccdc45646..0§&/"
   Decision: irrelevant
"""

    route_prompt = ChatPromptTemplate.from_messages([
       ("human", "Question: What are the main policies of the New Patriotic Party?\nDecision:"),
    ("assistant", "needs_context"),
    
    ("human", "Question: Tell me about the weather in Canada.\nDecision:"),
    ("assistant", "irrelevant"),
    
    ("human", "Question: Hey, how are you?\nDecision:"),
    ("assistant", "generic_response"),
    
    ("human", "Question: Hi, what can you help me with?\nDecision:"),
    ("assistant", "generic_response"),
    
    ("human", "Question: When is the 2024 election date?\nDecision:"),
    ("assistant", "needs_context"),
    
    ("human", "Question: rgasdgfccdc45646..0§&/\nDecision:"),
    ("assistant", "irrelevant"),
    
    ("human", "Question: Who are you?\nDecision:"),
    ("assistant", "generic_response"),
    
    ("human", "Question: What's the role of Parliament in Ghana?\nDecision:"),
    ("assistant", "needs_context"),
    
    ("human", "Question: Can you explain what you do?\nDecision:"),
    ("assistant", "generic_response"),
    
    ("human", "Question: Hello!\nDecision:"),
    ("assistant", "generic_response"),

    ("human", "Question: who has been the president in ghana in 2015\nDecision:"),
    ("assistant", "needs_context"),
    
    ("human", "Question: {question}\nDecision:")
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

def handle_generic_response(state):
    """
    Generate a generic response for simple questions that don't need context.

    Args:
        state (dict): The current graph state

    Returns:
        dict: Updated state with generation
    """
    logging.info("---GENERATING GENERIC RESPONSE---")
    question = state["question"]
    
    system = """You are an AI assistant focused on helping users with questions about Ghana's 2024 elections. 
    For simple greetings or general questions, provide a friendly response while mentioning your purpose. 
    You have acces to the offical perti manifestos and curated sources to help voters to make informed decisions. 
    You are a political neutral and do not take sides. Always just answer generically and do not use pretrsined knowledge to answer the question. 
    You are only answer questions about yourself. 
    More info abou you: 
     You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
     You are running on the OpenAI API using the GPT-4o model.
     You can't search the Web, but only retrive information via a retrieval augemnted generaion pipline form pre-indexed documents.
     """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),

        ("human", "Hello"),
        ("assistant", "Hey there, do you have any questions? I can help you browsing through my sources like manifestos and a curated selection of websites and articles!"),

        ("human", "Hello, who are you? "),
        ("assistant", "Hey, I m an AI assistant helping voters to inform themselves for the upcoming elections in Ghana. Do you have any questions?"),
        
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

def decide_to_generate(state):
    """
    Determines whether to generate an answer, or re-generate a question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    logging.info("---ASSESS GRADED DOCUMENTS---")
    state["question"]
    filtered_documents = state["documents"]

    if not filtered_documents:
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        logging.info(
            "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
        )
        return "transform_query"
    else:
        # We have relevant documents, so generate answer
        logging.info("---DECISION: GENERATE---")
        return "generate"


def grade_generation_v_documents_and_question(state):
    """
    Determines whether the generation is grounded in the document and answers question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """

    logging.info("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    
    # Ensure that hallucination grader is instantiated
    # class GradeHallucinations(BaseModel):
    #     """Binary score for hallucination present in generation answer."""

    #     binary_score: str = Field(
    #         description="Answer is grounded in the facts, 'yes' or 'no'"
    #     )
    # system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
    # hallucination_prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", system),
    #         ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    #     ]
    # )
    # hallucination_grader = hallucination_prompt | get_llm().with_structured_output(GradeHallucinations)

    # Ensure that answer grader is instantiated
    class GradeAnswer(BaseModel):
        """Binary score to assess wether the answer addresses the question."""

        binary_score: str = Field(
            description="Answer addresses the question, 'yes' or 'no'"
        )
    system = """You are a grader assessing whether an answer addresses / resolves a question. Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question, "No" means that the answer does not resolve the question.
    You are part of a RAG pipeline for a chatbot to help people infrm themselves for the elections in Ghana. 
    Ask yourself if the generation handed over to you is a good answer to the question. 
    It doesnt have to resolve the question entirely, 
    but it should be a good answer. Say no if the generation halucinates something nonsensical.
    
    
    """
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),



            ("human", """User question: \n\n Who was the president in 2009? \n\n LLM generation: \n\n  John Atta Mills was the President of Ghana in 2009.

He was elected in the 2008 elections and served as President until his death in July 2012, after which John Mahama, then Vice President, took over the presidency.

Source: Wahlen in Ghana.pdf"""),



    ("assistant", "yes"),




            ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
        ]
    )
    
    answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)

    # score = hallucination_grader.invoke(
    #     {"documents": "\n\n".join(documents), "generation": generation}
    # )
    # grade = score.binary_score
    grade = 'yes'

    
    # Check hallucination

    # Check question-answering
    

    if grade == "yes":
        logging.info("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        generation = state["generation"]

     
        if grade == "yes":
            logging.info("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            logging.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        logging.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        loopfix: boolean flag for loop control
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

def get_graph():
    if not hasattr(get_graph, 'app'):
        workflow = StateGraph(GraphState)

        # Define the nodes
        workflow.add_node("scoping", scoping)
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("grade_documents", grade_documents)
        workflow.add_node("generate", generate)
        workflow.add_node("generate2", generate2)

        workflow.add_node("transform_query", transform_query)
        workflow.add_node("handle_generic_response", handle_generic_response)  # New node




        # Build graph
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
        workflow.add_edge("handle_generic_response", END)  # Direct path to end for generic responses
        workflow.add_conditional_edges(
            "grade_documents",
            decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )

        # Initialize a counter variable
        transform_query_counter = 0

        # Define a function to handle the conditional logic
        def check_transform_query(state):
            if not 'loops' in state:
                state['loops'] = 0
            if state['loops'] >= 3:
                return "generate2"
            else:
                state['loops'] += 1
                return "retrieve"

        # Add conditional edges using the counter
        workflow.add_conditional_edges(
            "transform_query",
            check_transform_query,
            {
                "generate2": "generate2",
                "retrieve": "retrieve"
            }
        )

        workflow.add_conditional_edges(
            "generate",
            grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": END,
                "not useful": "transform_query",
            },
        )
        workflow.add_edge("generate2", END)


        # Compile
        get_graph.app = workflow.compile()
    
    return get_graph.app

if __name__ == "__main__":
    dotenv.load_dotenv()
    app = get_graph()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    config = RunnableConfig(recursion_limit=10)
    preamble = """Our algorithm has reach our self-imposed recursion limit of 10. 
    This means that we are not confident enough that the data in the context is enough to answer your question. 
    However, we will still provide the best answer we can given the data we have: \n\n"""  # Edit this text as needed
    try:
        for output in app.stream({'question': 'How does the New Patriotic Party want to improve the ghanaian economy?'}, config=config):
            for key, value in output.items():
                logging.info(f'Node: {key}\n---\n')
        print(value['generation'])
    except Exception as e:
        #logging.error("Graph recursion limit reached.")
        # Output the last generation with the preamble
        print(preamble)
        # if 'value' in locals():
        #     print(preamble + value['generation'])
        # else:
        #     print(preamble + value['generation'])