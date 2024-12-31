from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from connect_db import create_connection
from postgre_to_pinecone import create_embeddings
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import time
import threading
import os

model = SentenceTransformer('all-MiniLM-L12-v2')

load_dotenv()



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
from collections import defaultdict
from sentence_transformers import SentenceTransformer

# Kullanılacak model
model = SentenceTransformer('all-MiniLM-L12-v2')

def create_embeddings(data):
    embeddings = []
    grouped_orders = defaultdict(list)
    
    # Gelen veriyi işlerken, kullanıcı ve sipariş bilgilerini gruplayarak
    # her bir siparişteki ürünleri bir araya getireceğiz
    for row in data:
        user_id = row['user_id']
        user_name = row['user_name']
        order_date = row['order_date']
        product_name = row['product_name']
        product_category = row['product_category']
        order_id = row['order_id']
        
        # Her bir siparişi kullanıcı ve sipariş tarihi ile grupluyoruz
        key = (user_id, order_date)
        
        # Eğer bu kullanıcı ve tarih daha önce gruplanmadıysa, başlatıyoruz
        if key not in grouped_orders:
            grouped_orders[key] = {
                'user_name': user_name,
                'order_id': order_id,  # order_id'yi de kaydediyoruz
                'products': []  # Ürünler için boş liste
            }
        
        # Ürün bilgilerini ekliyoruz
        grouped_orders[key]['products'].append({
            'product_name': product_name,
            'category': product_category
        })
    
    # Gruplanmış veriler üzerinde işlem yapıyoruz
    for (user_id, order_date), details in grouped_orders.items():
        user_name = details['user_name']
        products = details['products']
        order_id = details['order_id']
        
        # Ürünlerin adlarını birleştiriyoruz (örneğin, "Shampoo (Hair) and Body Lotion (Personal Care)")
        products_text = " and ".join([f"{p['product_name']} ({p['category']})" for p in products])

        # Kullanıcı ve ürün bilgilerini birleştirerek metin oluşturuyoruz
        text = f"User {user_name} ordered {products_text} on {order_date}"
        
        # Bu metni model ile encode ediyoruz (embedding)
        embedding = model.encode(text)
        
        # Metadata'yı oluşturuyoruz (kullanıcı bilgileri ve ürünler)
        metadata = {
            "user_id": user_id,
            "user_name": user_name,
            "order_date": str(order_date),  # Date'i string formatına çeviriyoruz
            "products": [p['product_name'] for p in products],
            "categories": [p['category'] for p in products]
        }
        
        # Benzersiz bir ID oluşturuyoruz (user_id ve order_date birleştirilmiş)
        unique_id = f"{user_id}_{order_date}"

        # Son olarak, embedding ve metadata'yı bir arada Pinecone'a gönderebilmek için ekliyoruz
        embeddings.append((unique_id, embedding.tolist(), metadata))

    return embeddings

def upsert_to_pinecone(embeddings):
    try:
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pc = Pinecone(api_key=pinecone_api_key)
        index_name= "e-commerce"
        batch_size = 100
        
        index= pc.Index(index_name)

        for i in range(0, len(embeddings), batch_size):
            batch = embeddings[i:i + batch_size]
            index.upsert(vectors=batch, namespace="e-commerce")
            print(f"Batch {i//batch_size + 1} added successfully")
            
        return True
    except Exception as e:
        print(f"Error in upsert_to_pinecone: {e}")
        return False

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
    finally:
        connection.close()

def sync_with_pinecone():
    while True:
        try:
            # Değişen kayıtları al
            changed_records = fetch_changed_records()
            
            if changed_records:
                # Tüm kayıtlar için embeddingler oluştur
                embeddings = create_embeddings(changed_records)
                
                # Pinecone'a gönder
                if upsert_to_pinecone(embeddings):
                    # Başarılı işlemi işaretle
                    mark_as_processed(changed_records)
                    print(f"Processed {len(changed_records)} records")
            
            # Bir sonraki kontrolden önce bekle
            time.sleep(10)
            
        except Exception as e:
            print(f"Error in sync loop: {e}")
            time.sleep(10)  # Hata durumunda da bekle
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