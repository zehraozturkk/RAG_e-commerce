import psycopg2
import sys

def create_connection():
    try:
        connection =  psycopg2.connect(
            host="localhost",
            database="e-commerce",
            user="postgres",
            password="1234567891",
            port= 5432
        )
        print("connection succes")
        return connection

    except Exception as e:
        print(f"Connection error: {e}")
        
   
if __name__ == "__main__":
    connect = create_connection()
    print(connect)