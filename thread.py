import threading
import time
import queue
from faker import Faker
from connect_db import create_connection
from random import choice, randint
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, filename="data_updater.log", filemode="w", 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class UpdateData:

    def __init__(self):
        self.logger = logging.getLogger("UpdateData")
        self.fake = Faker()
        try:
            self.connection = create_connection()
            self.cursor = self.connection.cursor()
            self.order_queue = queue.Queue()
            self.logger.info("Database connection and queue initialized successfully")
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise


    def generate_user(self):
        thread_logger = logging.getLogger('UserGenerator')
        thread_logger.info("User generation thread started")
        try:
            while True:
                name = self.fake.name()
                self.cursor.execute(
                        "INSERT INTO users (user_name) VALUES (%s) RETURNING user_id",
                        (name, )
                    )
                result = self.cursor.fetchone()
                print(result)
                if result is None:
                    thread_logger.error("Failed to insert user - no ID returned")
                    continue

                user_id = result[0]
                self.connection.commit()
                
                thread_logger.info(f"New user created: {name} (ID: {user_id})")
                time.sleep(randint(1,5))
                #self.order_queue.put(user_id)
        except Exception as e:
            print(f"Error in generate_user: {e}")
            thread_logger.error(f"Error in generate_user: {e}")
    
    def insert_new_order(self):
        thread_logger = logging.getLogger('OrderGenerator')
        thread_logger.info("order generation thread started")

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
                        
                        order_ids = []
                        # Siparişi ekle
                        for product_id in selected_product_ids:
                            self.cursor.execute(
                                "INSERT INTO orders (user_id, product_id, order_date) VALUES (%s, %s, %s) RETURNING order_id",
                                (user_id, product_id, datetime.now())
                            )
                            order_ids.append(self.cursor.fetchone()[0])
                        self.connection.commit()
                        thread_logger.info(
                            f"New order created: User ID {user_id}, "
                            f"Product count: {product_count}, "
                            f"Order IDs: {order_ids}")
                    else:
                        thread_logger.warning("no products found in databse")
                else:
                    thread_logger.warning("no user found in databse")
                    
                time.sleep(randint(3, 5))  # Sipariş ekleme süresi
            except Exception as e:
                thread_logger.error(f"Error inserting order: {e}")

    def delete_outed_records(self):
        thread_logger = logging.getLogger('Cleaner')
        thread_logger.info("record cleaning thread started")
        try:
            while True:
                self.cursor.execute(
                    "DELETE FROM orders WHERE order_date < NOW() - INTERVAL '1 month' RETURNING order_id",
                )
                deleted_count = self.cursor.rowcount
                self.connection.commit()
                if deleted_count > 0:
                    thread_logger.info(f"Deleted {deleted_count} old orders")
                thread_logger.debug("Performed cleanup check")
                time.sleep(10)
        except Exception as e:
            thread_logger.error(f"error deleting old orders: {e}")

    def run_threads(self):
        self.logger.info("Starting all threads")
        user_thread = threading.Thread(target=self.generate_user, name="UserGenerator", daemon=True)
        order_thread = threading.Thread(target=self.insert_new_order, name="OrderGenerator" , daemon=True)
        delete_thread = threading.Thread(target=self.delete_outed_records, name="Cleaner", daemon=True)

        try:
            user_thread.start()
            order_thread.start()
            delete_thread.start()

            self.logger.info("All threads started succesfully")

            while True:
                time.sleep(0.1)  # Programın sürekli çalışmasını sağlar
        except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Error in thread management: {e}")
        finally:
            self.logger.info("Closing database connection")
            self.connection.close()
            self.logger.info("Program terminated")

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