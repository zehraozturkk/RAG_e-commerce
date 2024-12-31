from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import openai

# Ortam değişkenlerini yükle
load_dotenv()

# Model ve Pinecone kurulumu
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("e-commerce")
openai.api_key = os.getenv("OPENAI_API_KEY")
model = SentenceTransformer('all-MiniLM-L12-v2')



def search(top_k, query ):
    
    query_vector = model.encode(query).tolist()
    try:
        docs = index.query(
            vector=query_vector,
            top_k=top_k, 
            include_metadata=True,
            namespace="e-commerce",
            # filter= {"user_name":{"$eq":"Dana Smith"}}
        )
        matched_count = len(docs.matches)
        print(matched_count)
        retrieved_docs = []
        for doc in docs.get('matches', []):  # 'matched' yerine 'matches' kullanılmalı
                metadata = doc['metadata']
                score = doc['score']  # Benzerlik skorunu da alalım
                retrieved_docs.append({
                    'metadata': metadata,
                    'score': score
                })
        if not retrieved_docs:
                print("No results found. Checking index status...")
                debug_index()
                
        return retrieved_docs
    except Exception as e:
        print(f"Error during search: {str(e)}")
        debug_index()
        return []

def debug_index():
    """Index durumunu kontrol eder"""
    stats = index.describe_index_stats()
    print("Index Stats:", stats)
    return stats

def prompt_context_builder(query, docs):
    delim = '\n\n---\n\n'
    context = delim.join([
        f"User ID: {doc['metadata'].get('user_id')}, "
        f"User Name: {doc['metadata'].get('user_name')}, "
        f"Order Date: {doc['metadata'].get('order_date')}, "
        f"Products: {', '.join(doc['metadata'].get('products', []))}, "
        f"Categories: {', '.join(doc['metadata'].get('categories', []))}"
        for doc in docs
    ])
    prompt_start = f"Context:\n{context}\n\n"
    prompt_end = f"Question: {query}\nAnswer: Please analyze the e-commerce data and provide a clear answer."
    return prompt_start + prompt_end


def question_answering(prompt, chat_model):
    sys_prompt = "You are a helpful assistant that always answers questions."
    
    # Yeni API çağrısı
    res = openai.ChatCompletion.create(
        model=chat_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    answer = res['choices'][0]['message']['content'].strip()

    return answer


def analyze_logs(query, top_k=500):
    documents = search(
        query=query,
        top_k=top_k,
    )
    
    if not documents:
        return "No relevant data found for the query."

    prompt_with_context = prompt_context_builder(query, documents)
    
    answer = question_answering(
        prompt=prompt_with_context,
        chat_model='gpt-4-turbo'
    )
    
    return answer


if __name__ == "__main__":
    print("checikng index")
    debug_index()
    query = "How many orders has User Kathleen Bridges placed?"
    # result, mached = search(
    #     query=query,
    #     top_k=100,
    # )
    result = analyze_logs(query)
    print(result)