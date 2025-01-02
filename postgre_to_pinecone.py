import psycopg2
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os 
from connect_db import create_connection
from sentence_transformers import SentenceTransformer
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, filename="extract_data.log", filemode="w", 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')




class PineconeDataLoader:

    def __init__(self):
        self.logger = logging.getLogger("PineconeDataLoader")
        load_dotenv()   
        try: 
            self.model = SentenceTransformer('all-MiniLM-L12-v2')
            self.connection = create_connection()
            self.cursor = self.connection.cursor()
            self.logger.info("Database connection succesfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    



    def fetch_data_from_postgres(self):

        self.logger.info("starting data fetch from PostgreSQL")
        
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
        try:
            self.cursor.execute(query)
            data = self.cursor.fetchall()
            self.logger.info(f"Successfully retrieved {len(data)} records from database")
            return data
        except Exception as e:
            self.logger.error(f"Error retrieving data from database: {e}")
            raise
        finally:
            self.connection.close()

    def create_embeddings(self, data):
        embedding_list = []

        grouped_orders = defaultdict(list)
        try:
            for row in data:
                user_id, user_name, _, _, order_date, product_name, product_category = row
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
            self.logger.info(f"Grouped {len(grouped_orders)} unique user-date combinations")

            for (user_id, order_date), details in grouped_orders.items():
                products = details["products"]
                user_name = details['user_name']
                
                
                # Ürün bilgilerini birleştir, sadece dict olanları al
                products_text = " and ".join([
                    f"{p['product_name']} ({p['category']})"
                    for p in products if isinstance(p, dict)
                ])

                text = f"User {user_name} ordered {products_text} on {order_date}"

                #print(text)

                embedding = self.model.encode(text)
                
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
                embedding_list.append((unique_id, embedding.tolist(), metadata))
            
            self.logger.info(f"Successfully created {len(embedding_list)} embeddings")
            return embedding_list
        
        except Exception as e:
            self.logger.error(f"Error creating embeddings: {e}")
            raise
                

    def upload_to_pinecone(self, embeddings):
        self.logger.info("Starting Pinecone upload process")
        try:

            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if not pinecone_api_key:
                raise ValueError("PINECONE_API_KEY not found in environment variables")
            
            pc = Pinecone(api_key=pinecone_api_key)
            index_name= "ecommerce-2"

            if index_name not in pc.list_indexes().names():
                pc.create_index(
                    name=index_name,
                    dimension=384,  # Burada embedding boyutuna uygun 384 kullanılıyor
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            self.logger.info(f"Successfully created index '{index_name}'")

            index= pc.Index(index_name)

            batch_size=100
            total_batches = (len(embeddings) + batch_size - 1) // batch_size

            for i in range(0,len(embeddings), batch_size):
                batch = embeddings[i:i + batch_size]
                index.upsert(vectors=batch, namespace="e-commerce")
                current_batch = (i // batch_size) + 1
                self.logger.info(f"Uploaded batch {current_batch}/{total_batches}")

            self.logger.info("Successfully completed Pinecone upload")

        except Exception as e:
            self.logger.error(f"Error uploading to Pinecone: {e}")
            raise



def main():
    try:
        loader = PineconeDataLoader()
        
        data = loader.fetch_data_from_postgres()
        embeddings = loader.create_embeddings(data)
        loader.upload_to_pinecone(embeddings)
        
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()