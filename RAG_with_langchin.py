from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from pinecone import Pinecone
import os
from dotenv import load_dotenv

class RAGSystem:
    def __init__(self):
        load_dotenv()

        self.embeddings = HuggingFaceEmbeddings(model_name = "sentence-transformers/all-mpnet-base-v2")

        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = "ecommerce-2"
        self.vector_store = PineconeVectorStore(
            index_name= self.index_name,
            embedding=self.embeddings,
            namespace="ecommerce-22"
        )


        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.prompt_template = """
        Please analyze the e-commerce data in the backtick and provide a comprehensive answer. If multiple users have purchased the specified item, list ALL of them.
        If the documents dont match the answer say I dont know.


        context: `{context}`

        question: {question}

        Please provide a detailed answer that includes:
        - All users who made this purchase
        - Their purchase dates if available
        - Any other relevant details from the context
        - All requested products

        answer: """

        self.prompt = PromptTemplate(template=self.prompt_template, input_variables=["context", "question"])

        self.qa_chain = self._create_qa_chain()

    def _create_qa_chain(self):
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": 100}
            ),
            return_source_documents = True,
            chain_type_kwargs={
                "prompt": self.prompt
            }

        )
    
    def debug_index(self):
        """Index durumunu kontrol eder"""
        try:
            index = self.pc.Index(self.index_name)
            stats = index.describe_index_stats()
            print("\nIndex İstatistikleri:")
            print(f"Sum of vector: {stats.total_vector_count}")
            print(f"Namespaces: {stats.namespaces}")
            print(f"dimension: {stats.dimension}")
            return stats
        
        except Exception as e:
            print(f"Index istatistikleri alınırken hata: {str(e)}")
            return None
        
    def query(self, question):
        try:
            result = self.qa_chain.invoke({"query": question})
            
            print("\nKullanılan Kaynaklar:")
            for i, doc in enumerate(result["source_documents"], 1):
                print(f"\nKaynak {i}:")
                print(f"İçerik: {doc.page_content}")
                print(f"Metadata: {doc.metadata}")
                print(f"Skor: {doc.metadata.get('score', 'N/A')}")

            
            return {
                "answer": result["result"],
                "source_documents": result["source_documents"]
            }
            
        except Exception as e:
            print(f"Sorgu sırasında hata: {str(e)}")
            return {
                "answer": "Sorgu işlenirken bir hata oluştu.",
                "error": str(e)
            }

def main():
    rag = RAGSystem()
    
    rag.debug_index()
    
    test_queries = [
        "can you listed the names of users who buy a Shampoo (Yellow)",
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Sorgu: {query}")
        result = rag.query(query)
        print(f"\nCevap: {result['answer']}")

if __name__ == "__main__":
    main()