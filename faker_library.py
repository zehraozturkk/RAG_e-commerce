from faker import Faker
from connect_db import create_connection
from random import choice, randint
from datetime import datetime, timedelta


class DataGenerator:

    def __init__(self):
        self.fake=Faker()
        self.connection = create_connection()
        self.cursor = self.connection.cursor()
        
    def generate_users(self, num_users=100):
        users = []   
        try:     
            for _ in range(num_users):
                name = self.fake.name()
                self.cursor.execute(
                    "INSERT INTO users (user_name) VALUES (%s) RETURNING user_id",
                    (name, )
                )
                users.append(self.cursor.fetchone()[0])
            self.connection.commit()
            print("adding succes")
            return users
        
        except Exception as e:
            print(f"Error inserting data: {e}")

    def generate_products(self, num_products=500):


        categories = [
            "Clothing","Jewelry","Flower Type", "Electronics", "Home Goods", "Personal Care"
        ]

        # Products for each category
        products = {
            "Clothing": [
                "T-shirt", "V-neck T-shirt","Winter Coat", "Waterproof Coat", "Wool Coat", "Plus Size Coat", "Wool Sweater", "Buttoned Sweater",
                "Women Blazer", "Men Blazer","Jeans", "Straight Jeans", "Mom Jeans","Shirt", "Short Sleeve Shirt", "Long Sleeve Shirt", "Patterned Shirt"],
            "Jewelry": ["Necklace", "Bracelet", "Ring", "Earrings"],
            "Flower Type": ["Succulent", "Cactus", "Ficus", "Begonia","Daisy", "Rose", "Tulip", "Orchid"],
            "Electronics": ["Smartphone","Powerbank", "Laptop", "Bluetooth Headset", "Smartwatch", "keyword", "mouse"],
            "Stationery": ["Notebook", "Pen", "Backpack", "Colorful Post-it"],
            "Home Goods": ["Lamp", "Table Clock", "Curtain", "Carpet","Pot", "Knife Set", "Pitcher", "Food Processor"],
            "Personal Care": ["Shampoo", "Body Lotion", "Perfume", "Toothbrush"]
        }

        # 10 colors
        colors = ["Red", "Blue", "Green", "Yellow", "Black", "White", "Pink", "Purple", "Orange", "Brown"]
        try:
            products_list = []
            for _ in range(num_products):
                category = choice(categories)  
                product_name = choice(products[category])  
                color = choice(colors)  
                # Create the full product name with category and color
                product_full_name = f"{product_name} ({color})"
                self.cursor.execute(
                    "INSERT INTO products (product_name, category) VALUES (%s, %s) RETURNING product_id",
                    (product_full_name, category)
                )
                products_list.append(self.cursor.fetchone()[0])
            self.connection.commit()
            print(f"{len(products_list)} products successfully added to the database!")
            return products_list
            
        except Exception as e:
            print(f"Error inserting data: {e}")
    
    def generate_orders(self, users, products, order_count=1000):
        try:
            start_date = datetime.now() - timedelta(days=1)
            for _ in range(order_count):
                # Select random user
                user_id = choice(users)
                # Select random number of products (1-5)
                product_count = randint(1, 5)
                order_date = self.fake.date_time_between(
                    start_date=start_date,
                    end_date='now'
                )
                # Select random products - Fixed this line
                selected_products = [choice(products) for _ in range(product_count)]
                
                for product_id in selected_products:
                    self.cursor.execute(
                        "INSERT INTO orders (user_id, product_id, order_date) VALUES (%s, %s, %s)",
                        (user_id, product_id, order_date)
                    )
            self.connection.commit()
            print(f"{order_count} orders generated successfully.")

        except Exception as e:
            print(f"Error inserting data: {e}")


    def generate_all_data(self):
        print("genereting users")
        users= self.generate_users(100)

        print("Generating products...")
        products = self.generate_products(500)
        
        print("Generating orders...")
        self.generate_orders(users, products, 1000)
        
        print("Data generation completed!")
    
    def close_connection(self):
        self.cursor.close()
        self.connection.close()

if __name__ == "__main__":
    generator = DataGenerator()
    generator.generate_all_data()
    generator.close_connection()
