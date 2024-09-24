import mysql.connector
global cnx

cnx = mysql.connector.connect(
    host="localhost",
    user="root",
    password="MUK546@!",
    database="pandeyji_eatery"
)

def insert_order_item(food_item, quantity, next_order_id):
    try:
        cursor = cnx.cursor()
        
        cursor.callproc('insert_order_item', (food_item, quantity, next_order_id))
        cnx.commit()
        
        cursor.close()
        
        # print("Order item inserted sucessfully!")
        
        return 1
    except mysql.connector.Error as err:
        print(f"Error inserting food item: {err}")
        
        cnx.rollback()
        
        return -1
    except Exception as e:
        print(f"An error occured: {e}")
        
        cnx.rollback()
        
        return -1

def insert_order_tracking(order_id, status):
    cursor = cnx.cursor()
    
    insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
    cursor.execute(insert_query, (order_id, status))
    
    cnx.commit()
    
    cursor.close()


def get_total_order_price(order_id):
    cursor = cnx.cursor()
    
    query = f"SELECT get_total_order_price({order_id})"
    cursor.execute(query)
    
    result = cursor.fetchone()[0]
    
    cursor.close()
    
    return result

def get_next_order_id():
    cursor = cnx.cursor()
    
    query = "SELECT MAX(order_id) FROM orders"
    cursor.execute(query)
    
    result = cursor.fetchone()[0]
    
    cursor.close()
    
    if result is None:
        return 1
    else:
        return result + 1
    

# def get_order_status(order_id):
#     cursor = cnx.cursor()

#     query = f"SELECT status FROM order_tracking WHERE order_id = {order_id}"
#     query_price = f"SELECT get_total_order_price({order_id})"
#     cursor.execute(query, query_price)

#     result = cursor.fetchone()

#     cursor.close()
    
#     if result:
#         return result[0]
#     else:
#         return None
    
def get_order_status(order_id):
    cursor = cnx.cursor()

    # Combined query for status and total price
    query = f"""
    SELECT 
        ot.status, 
        get_total_order_price(ot.order_id) AS total_price 
    FROM 
        order_tracking ot 
    WHERE 
        ot.order_id = {order_id};
    """

    cursor.execute(query)
    result = cursor.fetchone()

    cursor.close()
    
    if result:
        # Returning both status and total price
        status, total_price = result
        return status, total_price      
    else:
        return None
