from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from connect_db import create_connection
from collections import defaultdict
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
import logging
from langchain_core.documents import Document
import time
import threading
import os


load_dotenv()
logger = logging.getLogger()


logging.basicConfig(level=logging.INFO, filename="upsert_pinecone.log", filemode="w", 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



def fetch_changed_records():
    connection = create_connection()
    cursor = connection.cursor()
    query = """
        SELECT 
            c.operation,
            u.user_id,
            u.user_name AS user_name,
            o.order_id,
            o.product_id,
            o.order_date,
            p.product_name AS product_name,
            p.category AS product_category
        FROM orders as o 
        JOIN change_log c ON c.record_id = o.order_id
        JOIN users u ON o.user_id = u.user_id
        JOIN products p ON o.product_id = p.product_id
        WHERE c.processed = FALSE
        ORDER BY c.change_time ASC;
    """
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    connection.close()
    return data


def prepare(data):
    documents = []
    grouped_orders = defaultdict(list)
    
    for row in data:
        user_id = row['user_id']
        user_name = row['user_name']
        order_date = row['order_date']
        product_name = row['product_name']
        product_category = row['product_category']
        order_id = row['order_id']
        
        key = (user_id, order_date)
        
        if key not in grouped_orders:
            grouped_orders[key] = {
                'user_name': user_name,
                'order_id': order_id, 
                'products': []  
            }
        
        grouped_orders[key]['products'].append({
            'product_name': product_name,
            'category': product_category
        })
    
    # Gruplanmış veriler üzerinde işlem yapıyoruz
    for (user_id, order_date), details in grouped_orders.items():
        user_name = details['user_name']
        products = details['products']
        order_id = details['order_id']
        
        products_text = " and ".join([
                    f"{p['product_name']} ({p['category']})"
                    for p in products if isinstance(p, dict)
                ])

        text = f"User {user_name} ordered {products_text} on {order_date}"
        
        #embedding = model.encode(text)
        
        metadata = {
            "user_id": user_id,
            "user_name": user_name,
            "order_date": str(order_date),  # Date'i string formatına çeviriyoruz
            "products": [p['product_name'] for p in products],
            "categories": [p['category'] for p in products]
        }
        
        doc = Document(
                    page_content = text,
                    metadata=metadata
                )
        
        documents.append(doc)
        logger.info(f"Successfully created {len(documents)} documents")
        # unique_id = f"{user_id}_{order_date}"

        # embeddings.append((unique_id, embedding.tolist(), metadata))

    return documents

def upsert_to_pinecone(documents):
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        index_name= "ecommerce-2"
        # batch_size = 100

        embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-mpnet-base-v2"
            ) 
        
        index= pc.Index(index_name)

        vector_store = PineconeVectorStore.from_documents(
                documents=documents,
                embedding=embeddings,
                index_name=index_name,
                namespace="ecommerce-22"
            )
        
        logger.info(f"Successfully completed Pinecone upload for {len(documents)} documents")

        # for i in range(0, len(embeddings), batch_size):
        #     batch = embeddings[i:i + batch_size]
        #     index.upsert(vectors=batch, namespace="e-commerce")
        #     print(f"Batch {i//batch_size + 1} added successfully")
            
        return vector_store
    except Exception as e:
        print(f"Error in upsert_to_pinecone: {e}")
        logger.error(f"Error uploading to Pinecone: {e}")
        raise

def mark_as_processed(processed_records):
    connection = create_connection()
    cursor = connection.cursor()
    
    try:
        order_ids = [record['order_id'] for record in processed_records]
        cursor.execute("""
            UPDATE change_log 
            SET processed = TRUE 
            WHERE record_id = ANY(%s)
        """, (order_ids,))
        connection.commit()
    except Exception as e:
        print(f"Error marking records as processed: {e}")
        logger.error(f"Error marking records as processed: {e}")
    finally:
        connection.close()

def sync_with_pinecone():
    while True:
        try:
            changed_records = fetch_changed_records()
            
            if changed_records:
                # Tüm kayıtlar için embeddingler oluştur
                documents = prepare(changed_records)

                vector_store = upsert_to_pinecone(documents)
                
                mark_as_processed(changed_records)
                logger.info(f"Processed {len(changed_records)} records")  
                # if upsert_to_pinecone(embeddings):
                #     # Başarılı işlemi işaretle
                #     mark_as_processed(changed_records)
                #     print(f"Processed {len(changed_records)} records")
            
                # Pinecone'a gönder
            # Bir sonraki kontrolden önce bekle
            time.sleep(10)
            
        except Exception as e:
            print(f"Error in sync loop: {e}")
            logger.error(f"Error in sync loop: {e}")
            time.sleep(10)  

def start_sync_service():
    thread = threading.Thread(target=sync_with_pinecone, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    sync_thread = start_sync_service()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down sync service...")