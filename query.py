from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import os
from dotenv import load_dotenv
from langchain.prompts.chat import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# Environment Variables
load_dotenv()

# Pinecone Setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("e-commerce")
model = SentenceTransformer('all-MiniLM-L12-v2')
llm = ChatOpenAI()

class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

# Structured LLM Grader
structured_llm_grader = llm.with_structured_output(GradeDocuments)

# System and Human Message Prompts
system_template = (
    "You are an evaluator determining the relevance of retrieved {documents} "
    "to a user's query {question}. If the document contains keywords or semantic "
    "meaning related to the question, mark it as relevant. Assign a binary score of "
    "'yes' or 'no' to indicate the document's relevance."
)
system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

human_message_prompt = HumanMessagePromptTemplate.from_template(
    input_variables=["documents", "question"],
    template="{question}",
)

grader_prompt = ChatPromptTemplate.from_messages(
    [system_message_prompt, human_message_prompt]
)

# Question Rewriter Prompt
rewrite_template = (
    "Given a user input {question}, rewrite or rephrase the question "
    "to optimize the query and improve content generation."
)
rewrite_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(rewrite_template),
    HumanMessagePromptTemplate.from_template(input_variables=["question"], template="{question}")
])

# Search Function
def search(query):
    query_vector = model.encode(query).tolist()
    try:
        docs = index.query(
            vector=query_vector,
            top_k=10,
            include_metadata=True,
            namespace="e-commerce"
        )
        retrieved_docs = []
        for doc in docs['matches']:
            metadata = doc.get('metadata', {})
            score = doc.get('score', 0)
            retrieved_docs.append({'metadata': metadata, 'score': score})
        return retrieved_docs
    except Exception as e:
        print(f"Error during search: {e}")
        return []

# Rewrite Query Function
def rewrite_query(query):
    question_rewriter = rewrite_prompt | llm | StrOutputParser()
    return question_rewriter.invoke({"question": query})

# Generate Answer Function
def generate_answer(docs, query):
    context = "\n".join([doc['metadata'].get('content', '') for doc in docs])
    answer_prompt_template = (
        "Given the following documents:\n{context}\n\n"
        "Answer the user's question: {question}"
    )
    answer_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(answer_prompt_template),
        HumanMessagePromptTemplate.from_template(input_variables=["context", "question"], template="{question}")
    ])
    answer_generator = answer_prompt | llm | StrOutputParser()
    return answer_generator.invoke({"context": context, "question": query})

# Query Handler
def handle_query(query):
    docs = search(query)
    if not docs:
        return "No results found."
    
    rewritten_query = rewrite_query(query)
    print(f"Rewritten Query: {rewritten_query}")
    
    answer = generate_answer(docs, rewritten_query)
    return answer

if __name__ == "__main__":
    user_query = "which users take the smartphone"
    response = handle_query(user_query)
    print(response)
