from sentence_transformers import SentenceTransformer
from connect_db import create_connection



class Embeddings:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        self.connection = create_connection()
        self.cursor = self.connection.cursor()

    def get_data(self):
        try:
            self.cursor.execute("SELECT product_name FROM products")
            product_names = self.cursor.fetchall()
            # Sadece ürün isimlerini alıyoruz
            product_names = [name[0] for name in product_names]
            return product_names
        except Exception as e:
            print(f"Error fetching data: {e}")
        finally:
            self.cursor.close()
            self.connection.close()

    def create_embeddings(self, product_names):
        try:
            # Ürün isimlerini vektörleştiriyoruz
            product_embeddings = self.model.encode(product_names)
            return product_embeddings
        except Exception as e:
            print(f"Error creating embeddings: {e}")

if __name__ == "__main__":
    embeddings = Embeddings()
    product_names = embeddings.get_data()
    if product_names:
        # Verileri vektörleştiriyoruz
        product_embeddings = embeddings.create_embeddings(product_names)
        print(product_embeddings[:5])  # İlk 5 ürünün vektörünü yazdır


