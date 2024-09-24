from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi import Request
import db_helper
import generic_helper



# Dictionary to store ongoing orders
inprogress_order = {}

app = FastAPI()
# @app.get("/")
# def read_root():
#     return {"message": "Hello, World!"}

# Dictionary to store ongoing orders
inprogress_order = {}

app = FastAPI()

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    
    session_id = generic_helper.extract_session_id(output_contexts[0]['name'])
    
    intent_handler_dict = {
        'new.order': start_new_order,  # Handle starting a new order
        'new.order.confirmation': handle_new_order_confirmation,  # Handle user confirmation
        'order.add - context: ongoing-order': add_to_order,
        'order.remove - context: ongoing-order': remove_order,
        'order.complete - context: ongoing-order': complete_order,
        'track.order - context ongoing-tracking': track_order
    }

    return intent_handler_dict[intent](parameters, session_id)

# Function to start a new order, clearing the previous order
def start_new_order(parameters: dict, session_id: str):
    # Clear any existing order for this session
    if session_id in inprogress_order:
        del inprogress_order[session_id]  # Remove the old order
    
    # Start a new order
    inprogress_order[session_id] = {}

    # Respond with confirmation message
    fulfillment_text = ("Ok, starting a new order. You can say things like "
                        "'I want two pizzas and one mango lassi'. "
                        "Make sure to specify a quantity for every food item! "
                        "Also, we have only the following items on our menu: "
                        "Pav Bhaji, Chole Bhature, Pizza, Mango Lassi, Masala Dosa, "
                        "Biryani, Vada Pav, Rava Dosa, and Samosa.")
    
    return JSONResponse(content={"fulfillmentText": fulfillment_text})

# Function to add items to the order
def add_to_order(parameters: dict, session_id: str):
    food_items = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_food_dict = dict(zip(food_items, quantities))

        # Check if an order exists, if not create a new order
        if session_id in inprogress_order:
            # Update existing order with new items
            current_food_dict = inprogress_order[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_order[session_id] = current_food_dict
        else:
            # If no ongoing order, create a new one
            inprogress_order[session_id] = new_food_dict

        order_str = generic_helper.get_str_from_food_dict(inprogress_order[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})

# Function to complete the order
def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        fulfillment_text = "I'm having trouble finding your order. Sorry! Can you place a new order, please?"
    else:
        order = inprogress_order[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. Please place a new order again. Thank you!"
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = (f"Thank you for ordering. We have placed your order. Here is your order id # {order_id}. "
                                f"Your order total is {int(order_total)}$, which you can pay at the time of delivery! Enjoy!")
        del inprogress_order[session_id]  # Clear the order after completion
        
    return JSONResponse(content={'fulfillmentText': fulfillment_text})

# Save the order to the database
def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()
    
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)

        if rcode == -1:
            return -1
        
    db_helper.insert_order_tracking(next_order_id, "In progress")
    
    return next_order_id

# Function to remove items from the order
def remove_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        return JSONResponse(content={'fulfillmentText': "I'm having trouble finding your order. Sorry! Can you place a new order, please?"})

    current_order = inprogress_order[session_id]
    food_items = parameters["food-item"]
    
    removed_items = []
    no_such_items = []
    
    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]
    
    fulfillment_text = ""
    if len(removed_items) > 0:
        fulfillment_text += f"Removed {', '.join(removed_items)} from your order!"

    if len(no_such_items) > 0:
        fulfillment_text += f" Your current order doesn't have {', '.join(no_such_items)}."
    
    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"
        
    return JSONResponse(content={'fulfillmentText': fulfillment_text})

# Function to track the order
def track_order(parameters: dict, session_id: str):
    order_id = int(parameters['number'])
    
    order_status, price = db_helper.get_order_status(order_id)
    
    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is {order_status} and you have to pay {int(price)}$ at the time of dilevery"
    else:
        fulfillment_text = f'No order found with order id: {order_id}'
    
    return JSONResponse(content={'fulfillmentText': fulfillment_text})

# Handle confirmation for a new order
def handle_new_order_confirmation(parameters: dict, session_id: str):
    confirmation = parameters.get('confirmation')

    if confirmation == "yes":
        # User confirmed to start a new order, clear the ongoing order
        inprogress_order[session_id] = {}
        fulfillment_text = "Starting a new order. What would you like to order?"
    else:
        # User chose to continue with the ongoing order
        current_order = inprogress_order[session_id]
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text = f"Continuing with your current order: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})