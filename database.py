import sqlite3
from datetime import datetime
import pandas as pd
import os
from pathlib import Path
import shutil

class Database:
    def __init__(self, db_path="inventory.db"):
        self.db_path = db_path
        # Create uploads directory if it doesn't exist
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity_purchased INTEGER NOT NULL,
                    date_purchased DATE NOT NULL,
                    total_purchase_price REAL NOT NULL,
                    variable_expenses REAL NOT NULL,
                    cost_per_unit REAL NOT NULL,
                    supplier TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create sales table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    sale_date DATE NOT NULL,
                    sale_price REAL NOT NULL,
                    price_per_unit REAL NOT NULL,
                    cost_per_unit REAL NOT NULL,
                    profit_per_unit REAL NOT NULL,
                    payment_type TEXT NOT NULL,
                    amount_received REAL NOT NULL,
                    amount_pending REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create credit_book table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credit_book (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date DATE NOT NULL,
                    due_date DATE NOT NULL,
                    description TEXT,
                    contact TEXT,
                    status TEXT DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Add documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_type TEXT NOT NULL,
                    reference_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Add contact_number column if it doesn't exist
            cursor.execute("PRAGMA table_info(credit_book)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'contact_number' not in columns:
                cursor.execute('ALTER TABLE credit_book ADD COLUMN contact_number TEXT')
            
            conn.commit()

    # Inventory Methods
    def add_inventory_item(self, item, category, quantity, date, total_price, expenses, cost_per_unit, supplier):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO inventory (
                    item, category, quantity_purchased, date_purchased,
                    total_purchase_price, variable_expenses, cost_per_unit, supplier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item, category, quantity, date, total_price, expenses, cost_per_unit, supplier))
            conn.commit()

    def get_inventory(self):
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM inventory", conn)

    # Sales Methods
    def add_sale(self, product_id, category, quantity, sale_date, sale_price, 
                 price_per_unit, cost_per_unit, profit_per_unit, 
                 payment_type, amount_received, amount_pending):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sales (
                    product_id, category, quantity, sale_date, sale_price,
                    price_per_unit, cost_per_unit, profit_per_unit,
                    payment_type, amount_received, amount_pending
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, category, quantity, sale_date, sale_price,
                  price_per_unit, cost_per_unit, profit_per_unit,
                  payment_type, amount_received, amount_pending))
            conn.commit()

    def get_sales(self):
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM sales", conn)

    # Credit Book Methods
    def add_credit(self, customer, contact_number, amount, date, due_date, status, description):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO credit_book (
                    customer, contact_number, amount, date, due_date, status, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (customer, contact_number, amount, date, due_date, status, description))
            conn.commit()

    def get_credit_book(self):
        """Get credit book with proper date formatting"""
        with self.get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM credit_book", conn)
            # Convert date strings to datetime objects
            df['date'] = pd.to_datetime(df['date'])
            df['due_date'] = pd.to_datetime(df['due_date'])
            return df

    def update_credit_status(self, credit_id, new_status):
        """Update the status of a credit entry"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Print debug information
                print(f"Updating credit {credit_id} to status: {new_status}")
                
                # First verify the credit exists
                cursor.execute("SELECT id FROM credit_book WHERE id = ?", (credit_id,))
                if not cursor.fetchone():
                    raise Exception(f"Credit with ID {credit_id} not found")
                
                # Update the status
                cursor.execute('''
                    UPDATE credit_book 
                    SET status = ? 
                    WHERE id = ?
                ''', (new_status, credit_id))
                
                # Verify the update
                cursor.execute("SELECT status FROM credit_book WHERE id = ?", (credit_id,))
                updated_status = cursor.fetchone()[0]
                print(f"Status updated to: {updated_status}")
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating credit status: {e}")
            raise e

    # Utility Methods
    def calculate_total_quantity(self, item):
        """Calculate current quantity for an item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total purchased
            cursor.execute('''
                SELECT COALESCE(SUM(quantity_purchased), 0)
                FROM inventory
                WHERE item = ?
            ''', (item,))
            total_purchased = cursor.fetchone()[0]
            
            # Get total sold
            cursor.execute('''
                SELECT COALESCE(SUM(quantity), 0)
                FROM sales
                WHERE product_id = ?
            ''', (item,))
            total_sold = cursor.fetchone()[0]
            
            return total_purchased - total_sold 

    def save_document(self, file, reference_type, reference_id):
        """Save a document to GitHub and record in database"""
        try:
            # Upload to GitHub
            file_url = self.storage.upload_file(
                file, 
                reference_type, 
                f"{reference_id}_{file.name}"
            )
            
            # Save reference in database
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO documents (
                        reference_type, reference_id, file_path, file_name
                    ) VALUES (?, ?, ?, ?)
                ''', (reference_type, reference_id, file_url, file.name))
                conn.commit()
            return True, "Document saved successfully"
        except Exception as e:
            return False, str(e)

    def get_documents(self, reference_type, reference_id):
        """Get documents for a reference"""
        with self.get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT * FROM documents 
                WHERE reference_type = ? AND reference_id = ?
                """, 
                conn, 
                params=(reference_type, reference_id)
            )
            return df

    def delete_document(self, document_id):
        """Delete document and its file"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Get file path before deletion
                cursor.execute("SELECT file_path FROM documents WHERE id = ?", (document_id,))
                result = cursor.fetchone()
                
                if result:
                    file_path = result[0]
                    # Delete file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Delete database record
                    cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                    conn.commit()
                    return True
                return False
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False 
