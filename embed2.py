from sentence_transformers import SentenceTransformer
import psycopg2
import numpy as np
import pandas as pd

class DataEmbedder:
    def __init__(self, connection_params):
        # Initialize the embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Connect to database
        self.conn = psycopg2.connect(**connection_params)
        self.cur = self.conn.cursor()

    def fetch_product_data(self):
        """Fetch product data from database"""
        query = """
        SELECT p.product_id, p.product_name, p.category,
               COUNT(o.order_id) as order_count
        FROM products p
        LEFT JOIN orders o ON p.product_id = o.product_id
        GROUP BY p.product_id, p.product_name, p.category
        """
        df = pd.read_sql(query, self.conn)
        return df

    def create_text_representation(self, row):
        """Create a text representation of a product"""
        return f"Product: {row['product_name']}, Category: {row['category']}, Orders: {row['order_count']}"

    def generate_embeddings(self):
        """Generate embeddings for all products"""
        # Fetch data
        df = self.fetch_product_data()
        
        # Create text representations
        texts = df.apply(self.create_text_representation, axis=1).tolist()
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Add embeddings to dataframe
        df['embedding'] = embeddings.tolist()
        
        return df

    def save_embeddings(self, df):
        """Save embeddings to database"""
        # Create embeddings table if it doesn't exist
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS product_embeddings (
            product_id INTEGER PRIMARY KEY,
            embedding VECTOR(384)
        )
        """)
        
        # Insert embeddings
        for _, row in df.iterrows():
            self.cur.execute(
                "INSERT INTO product_embeddings (product_id, embedding) VALUES (%s, %s) ON CONFLICT (product_id) DO UPDATE SET embedding = EXCLUDED.embedding",
                (row['product_id'], row['embedding'])
            )
        
        self.conn.commit()

    def close(self):
        """Close database connection"""
        self.cur.close()
        self.conn.close()

def main():
    # Database connection parameters
    connection_params = {
        "dbname": "retail_data",
        "user": "your_username",
        "password": "your_password",
        "host": "localhost"
    }
    
    # Initialize embedder
    embedder = DataEmbedder(connection_params)
    
    try:
        # Generate embeddings
        print("Generating embeddings...")
        df_with_embeddings = embedder.generate_embeddings()
        
        # Save embeddings
        print("Saving embeddings to database...")
        embedder.save_embeddings(df_with_embeddings)
        
        print("Embeddings generation completed!")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        embedder.close()

if __name__ == "__main__":
    main()