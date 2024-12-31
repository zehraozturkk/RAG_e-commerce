import threading
import time
import queue
from faker import Faker
from connect_db import create_connection
from random import choice, randint
from datetime import datetime, timedelta


class UpdateData:

    def __init__(self):
        self.fake = Faker()
        self.connection = create_connection()
        self.cursor = self.connection.cursor()
        self.order_queue = queue.Queue()

    def generate_user(self):
        try:
            while True:
                name = self.fake.name()
                self.cursor.execute(
                        "INSERT INTO users (user_name) VALUES (%s) RETURNING user_id",
                        (name, )
                    )
                user_id = self.cursor.fetchone()[0]
                self.connection.commit()
                
                print(f"Kullanıcı oluşturuldu: {name} (ID: {user_id})")
                time.sleep(randint(3,6))
                #self.order_queue.put(user_id)
        except Exception as e:
            print(f"Error in generate_user: {e}")
    
    def insert_new_order(self):
        while True:
            try:
                # Rastgele bir kullanıcı seç
                self.cursor.execute(
                    "SELECT user_id FROM users ORDER BY RANDOM() LIMIT 1"
                )
                user_result = self.cursor.fetchone()
                
                if user_result:
                    user_id = user_result[0]
                    product_count = randint(1, 5)
                    # Rastgele bir ürün seç
                    self.cursor.execute(
                        "SELECT product_id FROM products ORDER BY RANDOM() LIMIT %s",
                    (product_count,)
                )
                    product_results = self.cursor.fetchall()
                    
                    if product_results:
                        selected_product_ids = [product[0] for product in product_results]
                        
                        # Siparişi ekle
                        for product_id in selected_product_ids:
                            self.cursor.execute(
                                "INSERT INTO orders (user_id, product_id, order_date) VALUES (%s, %s, %s) RETURNING order_id",
                                (user_id, product_id, datetime.now())
                            )
                        order_id = self.cursor.fetchone()[0]
                        self.connection.commit()
                        print(f"Yeni {product_count} kadar ürünlü sipariş eklendi: Order ID {order_id} User ID {user_id}, Product ID {product_id}")
                    else:
                        print("No products found in database.")
                else:
                    print("No users found in database.")
                    
                time.sleep(randint(3, 5))  # Sipariş ekleme süresi
            except Exception as e:
                print(f"Error inserting order: {e}")

    # def delete_outed_records(self):
    #     try:
    #         while True:
    #             self.cursor.execute(
    #                 "DELETE FROM orders WHERE order_date < NOW() - INTERVAL '10 minutes' RETURNING order_id",
    #             )
    #             deleted_count = self.cursor.rowcount
    #             self.connection.commit()
    #             if deleted_count > 0:
    #                 print(f"deleted {deleted_count} old ordes")
    #             time.sleep(60)
    #     except Exception as e:
    #         print(f"error deleting old orders: {e}")
    def run_threads(self):

        user_thread = threading.Thread(target=self.generate_user, daemon=True)
        order_thread = threading.Thread(target=self.insert_new_order, daemon=True)
        # delete_thread = threading.Thread(target=self.delete_outed_records, daemon=True)

        user_thread.start()
        order_thread.start()
        # delete_thread.start()

        try:
            while True:
                time.sleep(0.1)  # Programın sürekli çalışmasını sağlar
        except KeyboardInterrupt:
                print("\nProgram sonlandırıldı.")
                self.connection.close()

if __name__ == "__main__":
    updater = UpdateData()
    updater.run_threads()


















# # Siparişlerin tutulduğu kuyruk
# order_queue = queue.Queue()

# def generate_orders():
#     """Yeni siparişler oluştur ve sıraya ekle."""
#     order_id = 1
#     while True:
#         time.sleep(1)  # Her saniyede bir sipariş oluştur
#         print(f"Yeni sipariş alındı: Order-{order_id}")
#         order_queue.put(f"Order-{order_id}")
#         order_id += 1

# def process_orders():
#     """Kuyruktaki siparişleri işle."""
#     while True:
#         order = order_queue.get()  # Kuyruktan bir sipariş al
#         print(f"Sipariş işleniyor: {order}")
#         time.sleep(2)  # İşleme süresi
#         print(f"Sipariş tamamlandı: {order}")
#         order_queue.task_done()

# # İş parçacıkları
# producer_thread = threading.Thread(target=generate_orders, daemon=True)
# consumer_thread = threading.Thread(target=process_orders, daemon=True)

# # İş parçacıklarını başlat
# producer_thread.start()
# consumer_thread.start()

# try:
#     # Program çalışırken ana iş parçacığını beklet
#     while True:
#         time.sleep(0.1)
# except KeyboardInterrupt:
#     print("\nProgram durduruldu.")


from threading import Thread, Lock, current_thread
import time
from queue import Queue

def worker(q):
    while True:
        value = q.get()

        #processing..

        print(f"in {current_thread().name} got {value}")
        q.task_done()

if __name__ == "__main__":
    q = Queue()
    q.put(1)
    q.put(2)
    q.put(3)

    # 3 2 1 -> 

    num_threads= 10

    for i in range(num_threads):
        thread = Thread(target=worker, args=(q,))
        thread.daemon=True
        thread.start()

    for i in range(1,12):
        q.put(i)

    q.join()