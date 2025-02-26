import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from database import Database
import time
from PIL import Image
import requests
from io import BytesIO
import base64

# Initialize database connection
db = Database()

# Debug function
def debug_dataframe(df, title="DataFrame Debug Info", show_debug=False):
    """Debug function that only shows information when show_debug is True"""
    if show_debug:
        st.write(f"=== {title} ===")
        st.write("Columns:", df.columns.tolist())
        st.write("Sample data:", df.head())
        st.write("Shape:", df.shape)

# Authentication
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

# Main app
if check_password():
    # Your existing app code starts here
    st.set_page_config(
        page_title="Business Management System",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Color scheme
    theme = {
        'bg_color': '#ffffff',
        'secondary_bg': '#f0f2f6',
        'sidebar_bg': '#f8f9fa',
        'text_color': '#1E3D59',
        'secondary_text': '#666666',
        'accent': '#2E7DAF',
        'success': '#28A745',
        'error': '#DC3545',
        'warning': '#FFC107'
    }

    # Define CSS
    css = f'''
    <style>
        /* Main layout */
        .main {{
            background-color: {theme['bg_color']};
            color: {theme['text_color']};
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {theme['sidebar_bg']};
            padding: 2rem 1rem;
        }}
        
        /* Headers */
        h1, h2, h3 {{
            color: {theme['text_color']} !important;
        }}
        
        /* Metrics */
        [data-testid="metric-container"] {{
            background-color: {theme['secondary_bg']};
            border: 1px solid {theme['accent']};
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        /* Buttons */
        .stButton > button {{
            background-color: {theme['accent']};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            border: none;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            background-color: {theme['accent']};
            opacity: 0.8;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
    </style>
    '''

    # Inject CSS
    st.markdown(css, unsafe_allow_html=True)

    # Keep the styled navigation in the sidebar section that uses emojis
    with st.sidebar:
        st.markdown(f"""
            <h1 style='color: {theme["text_color"]}; font-size: 1.8rem; margin-bottom: 2rem;'>
                📱 Navigation
            </h1>
        """, unsafe_allow_html=True)
        
        # Single navigation menu
        page = st.radio(
            "",
            [
                "🏠 Home",
                "📦 Inventory Management",
                "💰 Sales",
                "📒 Credit Book",
                "⚙️ Settings"
            ]
        )
        
        st.markdown("---")
        st.info("💼 Business Management System v1.0")

    # Get the actual page name without the icon
    page = ' '.join(page.split()[1:])  # Remove the emoji and keep the text

    # Initialize session state for inventory DataFrame with correct column names
    if 'inventory' not in st.session_state:
        st.session_state.inventory = db.get_inventory()

    # Initialize sales DataFrame with all required columns
    if 'sales' not in st.session_state:
        st.session_state.sales = db.get_sales()

    if 'credit_book' not in st.session_state:
        st.session_state.credit_book = db.get_credit_book()

    if 'categories' not in st.session_state:
        st.session_state.categories = ['General', 'Electronics', 'Clothing', 'Food']

    if 'suppliers' not in st.session_state:
        st.session_state.suppliers = ['General Supplier']

    # Initialize credit transactions DataFrame
    if 'credit_transactions' not in st.session_state:
        st.session_state.credit_transactions = pd.DataFrame(
            columns=[
                'Transaction_Date',
                'Product_ID',
                'Customer_Name',
                'Customer_Phone',
                'Total_Amount',
                'Amount_Received',
                'Amount_Pending',
                'Payment_Type',
                'Status'
            ])

    # Enhanced inventory management functions
    def calculate_cost_per_unit(total_price, variable_expenses, quantity):
        """Calculate cost per unit including variable expenses"""
        try:
            total_cost = total_price + variable_expenses
            return round(total_cost / quantity, 2) if quantity > 0 else 0
        except:
            return 0

    def add_item(item, category, quantity, date, total_purchase_price, variable_expenses, supplier):
        cost_per_unit = calculate_cost_per_unit(total_purchase_price, variable_expenses, quantity)
        db.add_inventory_item(
            item, category, quantity, date, total_purchase_price,
            variable_expenses, cost_per_unit, supplier
        )
        # Refresh session state
        st.session_state.inventory = db.get_inventory()

    def calculate_sale_metrics(product_id, quantity, sale_price):
        """Calculate price per unit and profit metrics"""
        try:
            # Get cost per unit from inventory
            item_data = st.session_state.inventory[
                st.session_state.inventory['Item'] == product_id
            ].iloc[-1]
            
            cost_per_unit = item_data['Cost Per Unit']
            price_per_unit = sale_price / quantity
            profit_per_unit = price_per_unit - cost_per_unit
            total_profit = profit_per_unit * quantity
            
            return {
                'Category': item_data['Category'],
                'Cost_Per_Unit': cost_per_unit,
                'Price_Per_Unit': price_per_unit,
                'Profit_Per_Unit': profit_per_unit,
                'Total_Profit': total_profit
            }
        except Exception as e:
            st.error(f"Error calculating metrics: {str(e)}")
            return None

    def record_sale(product_id, quantity, sale_date, sale_price, payment_type, amount_received, amount_pending):
        metrics = calculate_sale_metrics(product_id, quantity, sale_price)
        if metrics:
            db.add_sale(
                product_id, metrics['Category'], quantity, sale_date, sale_price,
                metrics['Price_Per_Unit'], metrics['Cost_Per_Unit'],
                metrics['Profit_Per_Unit'], payment_type, amount_received, amount_pending
            )
            # Refresh session state
            st.session_state.sales = db.get_sales()
            return True
        return False

    def calculate_total_quantity(item):
        """Calculate current quantity for an item"""
        total_purchased = st.session_state.inventory[st.session_state.inventory['Item'] == item]['Quantity Purchased'].sum()
        total_sold = st.session_state.sales[st.session_state.sales['Item'] == item]['Quantity Sold'].sum() if not st.session_state.sales.empty else 0
        return total_purchased - total_sold

    def add_credit(customer, amount, date, due_date, description, status="Pending"):
        db.add_credit(customer, amount, date, due_date, status, description)
        # Refresh session state
        st.session_state.credit_book = db.get_credit_book()

    def update_credit_status(credit_id, new_status):
        db.update_credit_status(credit_id, new_status)
        # Refresh session state
        st.session_state.credit_book = db.get_credit_book()

    def calculate_profit_margin(row):
        """Calculate profit margin percentage for a single item"""
        if row['Purchase Price'] > 0:
            margin = ((row['Selling Price'] - row['Purchase Price']) / row['Purchase Price'] * 100)
            return round(margin, 2)
        return 0

    def calculate_item_metrics(item_df):
        """Calculate various metrics for inventory items"""
        df = item_df.copy()
        
        # Calculate current quantity
        df['Current Quantity'] = df['Item'].apply(calculate_total_quantity)
        
        # Calculate total investment
        df['Total Investment'] = df['Purchase Price'] * df['Quantity Purchased']
        
        # Calculate potential revenue
        df['Potential Revenue'] = df['Selling Price'] * df['Current Quantity']
        
        # Calculate profit margin
        df['Profit Margin %'] = df.apply(calculate_profit_margin, axis=1)
        
        # Calculate potential profit
        df['Potential Profit'] = df['Potential Revenue'] - (df['Current Quantity'] * df['Purchase Price'])
        
        return df

    def calculate_inventory_status(inventory_df, sales_df):
        """Calculate current inventory status including sold and remaining quantities"""
        status_df = inventory_df.copy()
        
        # Initialize columns for tracking (update column names to match database)
        status_df['Total Purchased'] = status_df.groupby('item')['quantity_purchased'].transform('sum')
        status_df['Total Sold'] = 0
        status_df['Remaining Quantity'] = status_df['quantity_purchased']
        
        # Calculate total sold quantities from sales data
        if not sales_df.empty:
            sold_quantities = sales_df.groupby('product_id')['quantity'].sum()
            for item in status_df['item'].unique():
                if item in sold_quantities.index:
                    mask = status_df['item'] == item
                    status_df.loc[mask, 'Total Sold'] = sold_quantities[item]
                    status_df.loc[mask, 'Remaining Quantity'] = (
                        status_df.loc[mask, 'Total Purchased'] - sold_quantities[item]
                    )
        
        return status_df

    # Add this function to handle file display
    def display_documents(reference_type, reference_id):
        docs = db.get_documents(reference_type, reference_id)
        if not docs.empty:
            st.write("Attached Documents:")
            for _, doc in docs.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    file_url = doc['file_path']
                    if doc['file_name'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        try:
                            st.image(file_url, caption=doc['file_name'])
                        except:
                            st.error(f"Could not load image: {doc['file_name']}")
                    elif doc['file_name'].lower().endswith('.pdf'):
                        st.markdown(f"[📄 View PDF: {doc['file_name']}]({file_url})")
                    else:
                        st.markdown(f"[📎 Download: {doc['file_name']}]({file_url})")
                
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{doc['id']}"):
                        if db.delete_document(doc['id']):
                            st.success("Document deleted!")
                            time.sleep(1)
                            st.rerun()

    def view_document(url, file_type):
        """Display document based on its type"""
        try:
            if file_type in ['.png', '.jpg', '.jpeg', '.gif']:
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
                st.image(img, use_column_width=True)
            elif file_type == '.pdf':
                st.markdown(
                    f'<iframe src="{url}" width="100%" height="600px"></iframe>', 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(f"[Download File]({url})")
        except Exception as e:
            st.error(f"Error viewing document: {str(e)}")

    def upload_to_github(image_file, description="Uploaded image"):
        # Get token from Streamlit secrets
        token = st.secrets["github_token"]
        repo = "Shreya-MG/MG-Sanitory"
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        url = f"https://api.github.com/repos/{repo}/issues"
        file_content = base64.b64encode(image_file.read()).decode()
        
        data = {
            "title": f"Image Upload: {image_file.name}",
            "body": f"![{description}](data:image/{image_file.type};base64,{file_content})"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['html_url']
        except Exception as e:
            st.error(f"Upload failed: {str(e)}")
            return None

    # Home/Dashboard Page
    if page == "Home":
        st.title("Business Dashboard")
        
        # Top Level Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate metrics with safety checks
        with col1:
            total_inventory_value = (
                st.session_state.inventory['total_purchase_price'].sum() 
                if not st.session_state.inventory.empty else 0
            )
            st.metric("Total Inventory Value", f"₹{total_inventory_value:,.2f}")
        
        with col2:
            total_sales = (
                st.session_state.sales['sale_price'].sum() 
                if not st.session_state.sales.empty else 0
            )
            st.metric("Total Sales", f"₹{total_sales:,.2f}")
        
        with col3:
            if not st.session_state.sales.empty:
                if 'amount_pending' not in st.session_state.sales.columns:
                    st.session_state.sales['amount_pending'] = 0.0
                total_pending = st.session_state.sales['amount_pending'].sum()
            else:
                total_pending = 0
            st.metric("Total Pending", f"₹{total_pending:,.2f}")
        
        with col4:
            total_items = (
                len(st.session_state.inventory['item'].unique()) 
                if not st.session_state.inventory.empty else 0
            )
            st.metric("Total Items", total_items)

        # Add Credit Transactions Summary if exists
        if 'credit_transactions' in st.session_state and not st.session_state.credit_transactions.empty:
            st.subheader("Credit Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_credit = st.session_state.credit_transactions['Total_Amount'].sum()
                st.metric("Total Credit Amount", f"₹{total_credit:,.2f}")
            
            with col2:
                total_received = st.session_state.credit_transactions['Amount_Received'].sum()
                st.metric("Total Received", f"₹{total_received:,.2f}")
            
            with col3:
                total_pending = st.session_state.credit_transactions['Amount_Pending'].sum()
                st.metric("Total Pending", f"₹{total_pending:,.2f}")

        # Stock Movement Analysis
        st.subheader("Stock Movement Analysis")
        
        if not st.session_state.inventory.empty:
            # Prepare inventory data
            inventory_df = st.session_state.inventory.copy()
            sales_df = st.session_state.sales.copy() if not st.session_state.sales.empty else pd.DataFrame()
            
            # Calculate stock movement
            stock_movement = pd.DataFrame()
            stock_movement['product_id'] = inventory_df['item'].unique()
            
            # Calculate quantities
            stock_movement['quantity_bought'] = stock_movement['product_id'].apply(
                lambda x: inventory_df[inventory_df['item'] == x]['quantity_purchased'].sum()
            )
            
            stock_movement['quantity_sold'] = stock_movement['product_id'].apply(
                lambda x: sales_df[sales_df['product_id'] == x]['quantity'].sum() if not sales_df.empty else 0
            )
            
            stock_movement['quantity_remaining'] = stock_movement['quantity_bought'] - stock_movement['quantity_sold']
            
            # Add category information
            stock_movement['category'] = stock_movement['product_id'].apply(
                lambda x: inventory_df[inventory_df['item'] == x]['category'].iloc[0]
            )
            
            # Sort by remaining quantity
            stock_movement = stock_movement.sort_values('quantity_remaining', ascending=False)
            
            # Display filters
            col1, col2 = st.columns([2, 2])
            with col1:
                search = st.text_input("Search Products")
            with col2:
                category_filter = st.multiselect("Filter by Category", 
                                               options=stock_movement['category'].unique())
            
            # Apply filters
            if search:
                stock_movement = stock_movement[
                    stock_movement['product_id'].str.contains(search, case=False)
                ]
            if category_filter:
                stock_movement = stock_movement[stock_movement['category'].isin(category_filter)]
            
            # Display the stock movement table
            st.dataframe(
                stock_movement,
                column_config={
                    'product_id': st.column_config.TextColumn("Product ID"),
                    'category': st.column_config.TextColumn("Category"),
                    'quantity_bought': st.column_config.NumberColumn(
                        "Quantity Bought",
                        help="Total units purchased"
                    ),
                    'quantity_sold': st.column_config.NumberColumn(
                        "Quantity Sold",
                        help="Total units sold in selected period"
                    ),
                    'quantity_remaining': st.column_config.NumberColumn(
                        "Quantity Remaining",
                        help="Current available stock"
                    )
                },
                hide_index=True
            )
            
            # Show summary for filtered data
            st.subheader("Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Products", len(stock_movement))
            with col2:
                st.metric("Total Units Sold", f"{stock_movement['quantity_sold'].sum():,}")
            with col3:
                st.metric("Total Units Remaining", f"{stock_movement['quantity_remaining'].sum():,}")
        else:
            st.info("No inventory data available")

    # Inventory Management Page
    elif page == "Inventory Management":
        st.title("Inventory Management System")
        
        tab1, tab2, tab3 = st.tabs(["Add Inventory", "View Inventory", "Low Stock Alert"])
        
        with tab1:
            with st.form(key="add_item_form"):
                col1, col2 = st.columns(2)
                with col1:
                    item = st.text_input("Item Name")
                    category = st.selectbox("Category", options=st.session_state.categories)
                    quantity = st.number_input("Quantity", min_value=1, step=1)
                    date = st.date_input("Purchase Date", value=datetime.today())
                
                with col2:
                    total_purchase_price = st.number_input(
                        "Total Purchase Price", 
                        min_value=0.0, 
                        step=0.01,
                        help="Total amount paid for the entire purchase"
                    )
                    variable_expenses = st.number_input(
                        "Variable Expenses", 
                        min_value=0.0, 
                        step=0.01,
                        help="Additional expenses (transport, handling, etc.)"
                    )
                    supplier = st.selectbox("Supplier", options=st.session_state.suppliers)
                    
                    # Show real-time cost calculation
                    if quantity > 0 and (total_purchase_price > 0 or variable_expenses > 0):
                        cost_per_unit = calculate_cost_per_unit(total_purchase_price, variable_expenses, quantity)
                        st.write(f"Cost Per Unit: ₹{cost_per_unit:.2f}")
                        st.write(f"Total Cost: ₹{(total_purchase_price + variable_expenses):.2f}")
                
                # Add file upload field
                uploaded_files = st.file_uploader(
                    "Upload Bills/Documents", 
                    accept_multiple_files=True,
                    type=['png', 'jpg', 'jpeg', 'pdf']
                )
                
                submit = st.form_submit_button("Add Item")
                if submit:
                    if not item:
                        st.error("Item name is required!")
                    elif quantity <= 0:
                        st.error("Quantity must be greater than 0!")
                    elif total_purchase_price <= 0:
                        st.error("Purchase price must be greater than 0!")
                    else:
                        # Add item to inventory
                        add_item(item, category, quantity, date, total_purchase_price, 
                                variable_expenses, supplier)
                        
                        # Save uploaded files
                        if uploaded_files:
                            for file in uploaded_files:
                                success, message = db.save_document(
                                    file, 
                                    'inventory',
                                    st.session_state.inventory.index[-1]  # Get the last added item's ID
                                )
                                if success:
                                    st.success(f"Uploaded: {file.name}")
                                else:
                                    st.error(f"Failed to upload {file.name}: {message}")
                        
                        st.success(f"Added {quantity} units of {item} to inventory")

        with tab2:
            if not st.session_state.inventory.empty:
                # Search and filter
                col1, col2 = st.columns([2, 1])
                with col1:
                    search = st.text_input("Search Items")
                with col2:
                    category_filter = st.multiselect("Filter by Category", 
                                                   options=st.session_state.categories)
                
                # Calculate inventory status
                inventory_status = calculate_inventory_status(
                    st.session_state.inventory,
                    st.session_state.sales
                )
                
                # Apply filters
                if search:
                    inventory_status = inventory_status[
                        inventory_status['Item'].str.contains(search, case=False)
                    ]
                if category_filter:
                    inventory_status = inventory_status[
                        inventory_status['Category'].isin(category_filter)
                    ]
                
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Items", len(inventory_status['Item'].unique()))
                with col2:
                    total_investment = (inventory_status['Total Purchase Price'] + 
                                     inventory_status['Variable Expenses']).sum()
                    st.metric("Total Investment", f"₹{total_investment:,.2f}")
                with col3:
                    total_remaining = inventory_status['Remaining Quantity'].sum()
                    st.metric("Total Remaining Units", f"{total_remaining:,.0f}")
                with col4:
                    total_sold = inventory_status['Total Sold'].sum()
                    st.metric("Total Sold Units", f"{total_sold:,.0f}")
                
                # Display detailed inventory table
                st.subheader("Inventory Details")
                display_cols = [
                    'Item', 'Category', 'Quantity Purchased', 'Total Sold', 
                    'Remaining Quantity', 'Cost Per Unit', 'Total Purchase Price', 
                    'Variable Expenses', 'Supplier', 'Date Purchased'
                ]
                
                st.dataframe(
                    inventory_status[display_cols].sort_values('Remaining Quantity', ascending=False),
                    column_config={
                        'Cost Per Unit': st.column_config.NumberColumn(format="₹%.2f"),
                        'Total Purchase Price': st.column_config.NumberColumn(format="₹%.2f"),
                        'Variable Expenses': st.column_config.NumberColumn(format="₹%.2f"),
                        'Date Purchased': st.column_config.DateColumn("Purchase Date"),
                        'Remaining Quantity': st.column_config.NumberColumn(
                            "Remaining Stock",
                            help="Current available stock after sales"
                        ),
                        'Total Sold': st.column_config.NumberColumn(
                            "Total Sold",
                            help="Total units sold from this batch"
                        )
                    }
                )
                
                # Show stock movement visualization
                st.subheader("Stock Movement")
                movement_data = inventory_status.groupby('Item').agg({
                    'Total Purchased': 'sum',
                    'Total Sold': 'sum',
                    'Remaining Quantity': 'sum'
                }).reset_index()
                
                fig = go.Figure(data=[
                    go.Bar(name='Purchased', x=movement_data['Item'], y=movement_data['Total Purchased']),
                    go.Bar(name='Sold', x=movement_data['Item'], y=movement_data['Total Sold']),
                    go.Bar(name='Remaining', x=movement_data['Item'], y=movement_data['Remaining Quantity'])
                ])
                fig.update_layout(barmode='group', title='Stock Movement by Item')
                st.plotly_chart(fig)
                
                # Add document display for each item
                st.subheader("Item Documents")
                selected_item = st.selectbox(
                    "Select Item to View Documents",
                    options=st.session_state.inventory['Item'].unique()
                )
                if selected_item:
                    item_id = st.session_state.inventory[
                        st.session_state.inventory['Item'] == selected_item
                    ].index[0]
                    display_documents('inventory', item_id)
            else:
                st.info("No items in inventory")

        with tab3:
            st.subheader("Low Stock Alert")
            threshold = st.number_input("Low Stock Threshold", value=5, min_value=1)
            
            if not st.session_state.inventory.empty:
                inventory_status = calculate_inventory_status(
                    st.session_state.inventory,
                    st.session_state.sales
                )
                
                low_stock = inventory_status[
                    inventory_status['Remaining Quantity'] <= threshold
                ].copy()
                
                if not low_stock.empty:
                    st.warning(f"Items below threshold ({threshold} units)")
                    st.dataframe(
                        low_stock[['Item', 'Category', 'Remaining Quantity', 'Supplier']],
                        column_config={
                            'Remaining Quantity': st.column_config.NumberColumn(
                                "Remaining Stock",
                                help="Current available stock"
                            )
                        }
                    )
                else:
                    st.success("No items are running low on stock")

    # Sales Page
    if page == "Sales":
        st.title("Sales Management")
        
        tab1, tab2 = st.tabs(["Record Sale", "View Sales"])
        
        with tab1:
            with st.form("sales_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Get available items from inventory
                    available_items = st.session_state.inventory['item'].unique() if not st.session_state.inventory.empty else []
                    product_id = st.selectbox("Select Product", options=[''] + list(available_items))
                    
                    if product_id:
                        # Get item details from inventory
                        item_data = st.session_state.inventory[
                            st.session_state.inventory['item'] == product_id
                        ].iloc[-1]
                        
                        # Calculate available quantity
                        total_purchased = st.session_state.inventory[
                            st.session_state.inventory['item'] == product_id
                        ]['quantity_purchased'].sum()
                        
                        total_sold = 0
                        if not st.session_state.sales.empty:
                            total_sold = st.session_state.sales[
                                st.session_state.sales['product_id'] == product_id
                            ]['quantity'].sum()
                        
                        available_quantity = total_purchased - total_sold
                        cost_per_unit = item_data['cost_per_unit']
                        category = item_data['category']
                        
                        st.info(f"""
                        Available Quantity: {available_quantity} units
                        Cost Per Unit: ₹{cost_per_unit:,.2f}
                        Category: {category}
                        """)
                        
                        quantity = st.number_input("Quantity", 
                                                 min_value=1, 
                                                 max_value=available_quantity, 
                                                 step=1)
                        
                        sale_date = st.date_input("Sale Date", value=datetime.today())
                
                with col2:
                    if product_id:
                        sale_price = st.number_input("Total Sale Price", 
                                                   min_value=0.0,
                                                   step=0.01)
                        
                        # Payment type selection
                        payment_type = st.selectbox(
                            "Payment Type",
                            options=["Cash", "UPI", "Credit", "Partial"]
                        )
                        
                        # Show credit/partial payment fields if selected
                        if payment_type in ["Credit", "Partial"]:
                            st.write("---")
                            st.write("Credit Details")
                            customer_name = st.text_input("Customer Name", key="credit_customer_name")
                            customer_phone = st.text_input("Customer Phone", key="credit_customer_phone")
                            
                            if payment_type == "Credit":
                                amount_received = 0.0
                                amount_pending = sale_price
                                st.info(f"Full amount of ₹{sale_price:,.2f} will be added to credit")
                            else:  # Partial payment
                                amount_received = st.number_input(
                                    "Amount Received",
                                    min_value=0.0,
                                    max_value=sale_price,
                                    step=0.01
                                )
                                amount_pending = sale_price - amount_received
                                st.info(f"Pending amount: ₹{amount_pending:,.2f}")
                        else:
                            amount_received = sale_price
                            amount_pending = 0.0
                            customer_name = ""
                            customer_phone = ""
                        
                        # Calculate and display metrics
                        if quantity > 0 and sale_price > 0:
                            price_per_unit = sale_price / quantity
                            profit_per_unit = price_per_unit - cost_per_unit
                            total_profit = profit_per_unit * quantity
                            profit_margin = (profit_per_unit / cost_per_unit * 100)
                            
                            st.write("---")
                            st.write("Sale Summary")
                            st.write(f"""
                            Price Per Unit: ₹{price_per_unit:,.2f}
                            Profit Per Unit: ₹{profit_per_unit:,.2f}
                            Total Profit: ₹{total_profit:,.2f}
                            Profit Margin: {profit_margin:,.1f}%
                            """)
                
                # Add file upload field before the submit button
                st.write("---")
                uploaded_files = st.file_uploader(
                    "Upload Bills/Receipts", 
                    accept_multiple_files=True,
                    type=['png', 'jpg', 'jpeg', 'pdf']
                )
                
                # Submit button
                submitted = st.form_submit_button("Record Sale")
                
                if submitted:
                    try:
                        if not product_id:
                            st.error("Please select a product!")
                        elif sale_price <= 0:
                            st.error("Sale price must be greater than 0!")
                        elif quantity <= 0:
                            st.error("Quantity must be greater than 0!")
                        elif payment_type in ["Credit", "Partial"] and not customer_name:
                            st.error("Customer name is required for credit transactions!")
                        else:
                            # Record the sale
                            success = record_sale(
                                product_id, quantity, sale_date, sale_price,
                                payment_type, amount_received, amount_pending
                            )
                            if success:
                                # Handle file uploads
                                if uploaded_files:
                                    for file in uploaded_files:
                                        success, message = db.save_document(
                                            file, 
                                            'sales',
                                            st.session_state.sales.index[-1]  # Get the last added sale's ID
                                        )
                                        if success:
                                            st.success(f"Uploaded: {file.name}")
                                        else:
                                            st.error(f"Failed to upload {file.name}: {message}")
                                
                                st.success(f"Recorded sale of {quantity} {product_id}")
                                if amount_pending > 0:
                                    st.info(f"Added ₹{amount_pending:,.2f} to credit book")
                                st.rerun()
                            else:
                                st.error("Failed to record sale")
                    except Exception as e:
                        st.error(f"Error recording sale: {str(e)}")

        with tab2:
            if not st.session_state.sales.empty:
                # Ensure all required columns exist
                required_columns = [
                    'Product_ID', 'Category', 'Quantity', 'Sale_Date', 'Sale_Price',
                    'Price_Per_Unit', 'Cost_Per_Unit', 'Profit_Per_Unit',
                    'Payment_Type', 'Amount_Received', 'Amount_Pending'
                ]
                
                # Add missing columns with default values
                df = st.session_state.sales.copy()
                for col in required_columns:
                    if col not in df.columns:
                        if col in ['Payment_Type']:
                            df[col] = 'Cash'  # Default payment type
                        elif col in ['Amount_Received']:
                            df[col] = df['Sale_Price']  # Assume full payment for old entries
                        elif col in ['Amount_Pending']:
                            df[col] = 0.0  # Assume no pending amount for old entries
                        else:
                            df[col] = None  # For any other missing columns
                
                # Search and filter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    search = st.text_input("Search by Product ID")
                with col2:
                    category_filter = st.multiselect("Filter by Category", 
                                                   options=df['Category'].unique())
                with col3:
                    payment_filter = st.multiselect("Filter by Payment Type",
                                                  options=df['Payment_Type'].unique())
                
                # Apply filters
                if search:
                    df = df[df['Product_ID'].str.contains(search, case=False)]
                if category_filter:
                    df = df[df['Category'].isin(category_filter)]
                if payment_filter:
                    df = df[df['Payment_Type'].isin(payment_filter)]
                
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Sales", f"₹{df['Sale_Price'].sum():,.2f}")
                with col2:
                    st.metric("Amount Received", f"₹{df['Amount_Received'].sum():,.2f}")
                with col3:
                    st.metric("Amount Pending", f"₹{df['Amount_Pending'].sum():,.2f}")
                with col4:
                    st.metric("Total Profit", 
                             f"₹{(df['Profit_Per_Unit'] * df['Quantity']).sum():,.2f}")
                
                # Display detailed sales table
                st.subheader("Sales Details")
                st.dataframe(
                    df.sort_values('Sale_Date', ascending=False),
                    column_config={
                        'Sale_Price': st.column_config.NumberColumn(format="₹%.2f"),
                        'Price_Per_Unit': st.column_config.NumberColumn(format="₹%.2f"),
                        'Cost_Per_Unit': st.column_config.NumberColumn(format="₹%.2f"),
                        'Profit_Per_Unit': st.column_config.NumberColumn(format="₹%.2f"),
                        'Amount_Received': st.column_config.NumberColumn(format="₹%.2f"),
                        'Amount_Pending': st.column_config.NumberColumn(format="₹%.2f"),
                        'Sale_Date': st.column_config.DateColumn("Sale Date"),
                        'Payment_Type': st.column_config.TextColumn("Payment Type", help="Type of payment")
                    },
                    hide_index=True
                )
                
                # Add document display for sales
                st.subheader("Sale Documents")
                selected_sale = st.selectbox(
                    "Select Sale to View Documents",
                    options=st.session_state.sales.index,
                    format_func=lambda x: f"Sale {x}: {st.session_state.sales.loc[x, 'product_id']} - {st.session_state.sales.loc[x, 'sale_date']}"
                )
                if selected_sale is not None:
                    display_documents('sales', selected_sale)
            else:
                st.info("No sales recorded")

    # Credit Book Page
    elif page == "Credit Book":
        st.title("Credit Book")
        
        tab1, tab2, tab3 = st.tabs(["Add Credit", "Active Credits", "Settled Bills"])
        
        with tab1:
            with st.form(key="add_credit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    customer = st.text_input("Customer Name*")
                    contact = st.text_input(
                        "Contact Number",
                        placeholder="Enter 10-digit number",
                        help="Enter customer's contact number"
                    )
                    amount = st.number_input("Amount*", min_value=0.0, step=0.01)
                    date = st.date_input("Credit Date*", value=datetime.today())
                
                with col2:
                    due_date = st.date_input("Due Date*", value=datetime.today())
                    description = st.text_area(
                        "Description",
                        placeholder="Enter transaction details"
                    )
                
                # Add file upload for credit documents
                uploaded_files = st.file_uploader(
                    "Upload Documents", 
                    accept_multiple_files=True,
                    type=['png', 'jpg', 'jpeg', 'pdf']
                )
                
                submit = st.form_submit_button("Add Credit")
                if submit:
                    if not customer:
                        st.error("Customer name is required!")
                    elif amount <= 0:
                        st.error("Amount must be greater than 0!")
                    elif contact and not contact.isdigit():
                        st.error("Contact number should only contain digits!")
                    elif contact and len(contact) != 10:
                        st.error("Contact number should be 10 digits!")
                    else:
                        try:
                            # Add credit entry and get the new credit ID
                            credit_id = add_credit(
                                customer=customer,
                                amount=amount,
                                date=date,
                                due_date=due_date,
                                description=description,
                                contact=contact,
                                status="Pending"
                            )
                            
                            # Handle file uploads
                            if uploaded_files:
                                for file in uploaded_files:
                                    if file.type.startswith('image/'):
                                        st.image(file, caption=file.name, width=200)
                                        image_url = upload_to_github(file)
                                        if image_url:
                                            success, message = db.save_document(image_url, 'credit', credit_id)
                                            if success:
                                                st.success(f"Image uploaded: {file.name}")
                                            else:
                                                st.error(f"Failed to save document reference: {message}")
                                    elif file.type == 'application/pdf':
                                        st.markdown(f"📄 {file.name} ready for upload")
                                    
                                    success, message = db.save_document(file, 'credit', credit_id)
                                    if success:
                                        st.success(f"Uploaded: {file.name}")
                                    else:
                                        st.error(f"Failed to upload {file.name}: {message}")
                        
                            st.success(f"Added credit entry for {customer}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding credit: {str(e)}")

        with tab2:  # Active Credits
            if not st.session_state.credit_book.empty:
                # Filter for active (non-paid) credits
                active_credits = st.session_state.credit_book[
                    st.session_state.credit_book['status'] != 'Paid'
                ].copy()  # Make a copy to avoid SettingWithCopyWarning
                
                if not active_credits.empty:
                    # Summary metrics for active credits
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Active Credits", len(active_credits))
                    with col2:
                        total_pending = active_credits['amount'].sum()
                        st.metric("Total Pending Amount", f"₹{total_pending:,.2f}")
                    with col3:
                        overdue_count = len(active_credits[active_credits['status'] == 'Overdue'])
                        st.metric("Overdue Credits", overdue_count)
                    
                    st.markdown("---")
                    
                    # Display active credits
                    for _, row in active_credits.iterrows():
                        credit_id = row['id']  # Get the actual database ID
                        with st.expander(
                            f"{row['customer']} - ₹{row['amount']:,.2f} ({row['status']})"
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"Description: {row['description']}")
                                st.write(f"Date: {pd.to_datetime(row['date']).strftime('%Y-%m-%d')}")
                                st.write(f"Due Date: {pd.to_datetime(row['due_date']).strftime('%Y-%m-%d')}")
                                if 'contact' in row and row['contact']:
                                    st.write(f"📞 Contact: {row['contact']}")
                            
                            with col2:
                                current_status = row['status']
                                st.write(f"Current Status: {current_status}")
                                
                                # Add a separate button just for payment confirmation
                                if st.button("💰 Mark as Paid", key=f"pay_{credit_id}"):
                                    try:
                                        # Update the database using the actual credit_id
                                        db.update_credit_status(credit_id, 'Paid')
                                        # Force refresh the session state
                                        st.session_state.credit_book = db.get_credit_book()
                                        st.success("Payment confirmed! Bill settled successfully.")
                                        time.sleep(1)  # Give the user time to see the success message
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to update status: {str(e)}")
                                
                                # Separate button for marking as overdue
                                if current_status != 'Overdue' and st.button("⚠️ Mark as Overdue", key=f"overdue_{credit_id}"):
                                    try:
                                        db.update_credit_status(credit_id, 'Overdue')
                                        st.session_state.credit_book = db.get_credit_book()
                                        st.warning("Marked as overdue!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to update status: {str(e)}")
                            
                            # Display documents
                            display_documents('credit', credit_id)
                else:
                    st.success("No active credits - All bills are settled!")

        with tab3:  # Settled Bills
            if not st.session_state.credit_book.empty:
                # Filter for paid credits
                settled_credits = st.session_state.credit_book[
                    st.session_state.credit_book['status'] == 'Paid'
                ].sort_values('date', ascending=False)
                
                if not settled_credits.empty:
                    # Summary metrics for settled credits
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Settled Credits", len(settled_credits))
                    with col2:
                        total_settled = settled_credits['amount'].sum()
                        st.metric("Total Settled Amount", f"₹{total_settled:,.2f}")
                    
                    st.markdown("---")
                    
                    # Add search and filter options
                    col1, col2 = st.columns(2)
                    with col1:
                        search = st.text_input("Search by Customer Name")
                    with col2:
                        try:
                            # Convert dates to datetime.date for the date_input
                            min_date = pd.to_datetime(settled_credits['date'].min()).date()
                            max_date = pd.to_datetime(settled_credits['date'].max()).date()
                            date_range = st.date_input(
                                "Filter by Date Range",
                                value=(min_date, max_date),
                                key="settled_date_range"
                            )
                        except Exception as e:
                            st.error(f"Error with date range: {str(e)}")
                            date_range = None
                    
                    # Apply filters
                    filtered_credits = settled_credits
                    if search:
                        filtered_credits = filtered_credits[
                            filtered_credits['customer'].str.contains(search, case=False)
                        ]
                    if date_range and len(date_range) == 2:
                        try:
                            filtered_credits = filtered_credits[
                                (pd.to_datetime(filtered_credits['date']).dt.date >= date_range[0]) &
                                (pd.to_datetime(filtered_credits['date']).dt.date <= date_range[1])
                            ]
                        except Exception as e:
                            st.error(f"Error filtering dates: {str(e)}")
                    
                    # Display settled credits
                    for _, row in filtered_credits.iterrows():
                        credit_id = row['id']
                        with st.expander(
                            f"{row['customer']} - ₹{row['amount']:,.2f} (Settled)"
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"Description: {row['description']}")
                                try:
                                    credit_date = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                                    due_date = pd.to_datetime(row['due_date']).strftime('%Y-%m-%d')
                                    st.write(f"Credit Date: {credit_date}")
                                    st.write(f"Due Date: {due_date}")
                                except Exception as e:
                                    st.write("Date format error")
                            
                            # Display documents
                            display_documents('credit', credit_id)
                            
                            # Option to reactivate if needed
                            if st.button("Reactivate Credit", key=f"reactivate_{credit_id}"):
                                db.update_credit_status(credit_id, 'Pending')
                                st.session_state.credit_book = db.get_credit_book()
                                st.warning("Credit reactivated!")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("No settled bills yet")
            else:
                st.info("No credit entries")

    # Analysis Page
    elif page == "Analysis":
        st.title("Analysis Dashboard")
        
        # Key Metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_inventory_value = (st.session_state.inventory['total_purchase_price'] * 
                                   st.session_state.inventory['quantity_purchased']).sum()
            st.metric("Total Inventory Value", f"₹{total_inventory_value:,.2f}")
        
        with col2:
            total_sales = (st.session_state.sales['sale_price'] * 
                          st.session_state.sales['quantity']).sum() if not st.session_state.sales.empty else 0
            st.metric("Total Sales", f"₹{total_sales:,.2f}")
        
        with col3:
            total_credit = st.session_state.credit_book['amount'].sum() if not st.session_state.credit_book.empty else 0
            st.metric("Total Credit", f"₹{total_credit:,.2f}")

        # Sales Analysis
        if not st.session_state.sales.empty:
            st.subheader("Sales Trends")
            sales_df = st.session_state.sales.copy()
            sales_df['Date Sold'] = pd.to_datetime(sales_df['Date Sold'])
            daily_sales = sales_df.groupby('Date Sold').agg({
                'quantity': 'sum',
                'sale_price': lambda x: (x * sales_df.loc[x.index, 'quantity']).sum()
            }).reset_index()
            
            fig = px.line(daily_sales, x='Date Sold', y='sale_price', 
                         title='Daily Sales Revenue')
            st.plotly_chart(fig)

        # Inventory Analysis
        if not st.session_state.inventory.empty:
            st.subheader("Inventory by Category")
            category_data = st.session_state.inventory.groupby('Category')['quantity_purchased'].sum()
            fig = px.pie(values=category_data.values, names=category_data.index, 
                         title='Inventory Distribution by Category')
            st.plotly_chart(fig)