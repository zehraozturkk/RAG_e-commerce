from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import logging
import os
from dotenv import load_dotenv
from connect_db import create_connection
from collections import defaultdict
from langchain_core.documents import Document



logging.basicConfig(level=logging.INFO, filename="extract_data.log", filemode="w", 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')




class PineconeDataLoader:

    def __init__(self):
        self.logger = logging.getLogger("PineconeDataLoader")
        load_dotenv()   
        try: 
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-mpnet-base-v2"
            )

            self.connection = create_connection()
            self.cursor = self.connection.cursor()
            self.logger.info("Database connection succesfully")

            self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
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

    def prepare_documents(self, data):
        documents = []
        grouped_orders = defaultdict(list)

        try:
            for row in data:
                user_id, user_name, _, _, order_date, product_name, product_category = row
                key = (user_id, order_date)

                if key not in grouped_orders:
                    grouped_orders[key] = {
                        'user_name': user_name,  # Kullanıcı adı 
                        'products': []          
                    }

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

                
                # Metadata hazırla
                metadata = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "order_date": str(order_date),
                    "products": [p['product_name'] for p in products if isinstance(p, dict)],
                    "categories": [p['category'] for p in products if isinstance(p, dict)]
                }

                doc = Document(
                    page_content = text,
                    metadata=metadata
                )
                documents.append(doc)
                # print(documents)
            
            self.logger.info(f"Successfully created {len(documents)} embeddings")
            return documents
        
        except Exception as e:
            self.logger.error(f"Error preparing documents: {e}")
            raise

    def create_pinecone_index(self):
        try:
            index_name= "ecommerce-22"
            if index_name not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=index_name,
                    dimension=768,  # Burada embedding boyutuna uygun 384 kullanılıyor
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                self.logger.info(f"Successfully created index '{index_name}'")
            else:
                self.logger.info("this index was exist: {index_name}")
        except Exception as e:
            self.logger.error(f"Error creating to Pinecone index: {e}")
            raise



    def upload_to_pinecone(self, documents):
        self.logger.info("Starting Pinecone upload process")
        try:
            index_name= "ecommerce-2"

            vector_store = PineconeVectorStore.from_documents(
                documents=documents,
                embedding=self.embeddings,
                index_name=index_name,
                namespace="ecommerce-22"
            )

            # vector_store = PineconeVectorStore(index=index, embedding=self.embeddings)
            # uuids = [str(uuid4()) for _ in range(len(documents))]
            
            # vector_store.add_documents(documents=documents, ids=uuids)

            self.logger.info(f"Successfully completed {len(documents)} Pinecone upload")

            return vector_store

        except Exception as e:
            self.logger.error(f"Error uploading to Pinecone: {e}")
            raise



def main():
    try:
        loader = PineconeDataLoader()
        data = loader.fetch_data_from_postgres()
        loader.create_pinecone_index()
        documents = loader.prepare_documents(data)
        loader.upload_to_pinecone(documents)
        loader.cursor.close()
        loader.connection.close()
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()