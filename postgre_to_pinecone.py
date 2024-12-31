import psycopg2
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os 
from connect_db import create_connection
from sentence_transformers import SentenceTransformer
from collections import defaultdict

model = SentenceTransformer('all-MiniLM-L12-v2')

load_dotenv()



def fetch_data_from_postgres():
    connection = create_connection()
    cursor = connection.cursor()
    query = """
        -- her sipariş kullanıcı ve ürün bilgileir ile birleşir
SELECT
    u.user_id,
    u.user_name AS user_name,
    o.order_id,
    o.product_id,
    o.order_date,
    p.product_name AS product_name,
    p.category AS product_category
FROM
    orders o
JOIN
    users u ON o.user_id = u.user_id
JOIN
    products p ON o.product_id = p.product_id
ORDER BY 
    o.order_date DESC;
        """
    cursor.execute(query)
    data = cursor.fetchall()
    print("veri alınıd")
    connection.close()
    return data

def create_embeddings(data):
    embeddings = []

    grouped_orders = defaultdict(list)
    for row in data:
        user_id, user_name, order_date, product_name, product_category = row
        key = (user_id, order_date)

        if key not in grouped_orders:
            grouped_orders[key] = {
                'user_name': user_name,  # Kullanıcı adı ekleniyor
                'products': []          # Ürünler için boş liste
            }

    # Ürün bilgisi ekleniyor
        grouped_orders[key]['products'].append({
            'product_name': product_name,
            'category': product_category
        })

    for (user_id, order_date), details in grouped_orders.items():
        user_name = details['user_name']
        products = details['products']
        
        # Ürün bilgilerini birleştir, sadece dict olanları al
        products_text = " and ".join([
            f"{p['product_name']} ({p['category']})"
            for p in products if isinstance(p, dict)
        ])

    
        text = f"User {user_name} ordered {products_text} on {order_date}"
        #print(text)

        embedding = model.encode(text)
        
        # Metadata hazırla
        metadata = {
            "user_id": user_id,
            "user_name": user_name,
            "order_date": str(order_date),
            "products": [p['product_name'] for p in products if isinstance(p, dict)],
            "categories": [p['category'] for p in products if isinstance(p, dict)]
        }
        # print(metadata)

        unique_id = f"{user_id}_{order_date}"
        embeddings.append((unique_id, embedding.tolist(), metadata))
        
        # embeddings.append((user_id, embedding, metadata))

    return embeddings

    #return embeddings

    # for row in data:
    #     user_id,user_name,order_id, order_date, product_id, product_name, product_category = row


    #     text = f"User {user_name} ordered {product_name} ({product_category}) on {order_date}"
    #     embedding = model.encode(text)
    #     metadata = {
    #         "user_name": user_name,
    #         "order_date": str(order_date),
    #         "product_name": product_name,
    #         "product_category": product_category
    #     }
    #     embeddings.append((user_name, embedding, metadata))
    #     return row

def uploud_to_pinecone(embeddings):
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pc = Pinecone(api_key=pinecone_api_key)
    index_name= "e-commerce"

    if index_name in pc.list_indexes():
        print(f"Index '{index_name}' mevcut, siliniyor...")
        pc.delete_index(index_name)

    pc.create_index(
        name=index_name,
        dimension=384,  # Burada embedding boyutuna uygun 384 kullanılıyor
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    print(f"Index '{index_name}' mevcut veya başarıyla oluşturuldu.")

    index= pc.Index(index_name)

    batch_size=100

    for i in range(0,len(embeddings), batch_size):
        batch = embeddings[i:i + batch_size]

        index.upsert(vectors=batch, namespace="e-commerce")
        print("added")






if __name__ =="__main__":
        
    data = fetch_data_from_postgres()
    embed = create_embeddings(data)
    uploud_to_pinecone(embed)

 