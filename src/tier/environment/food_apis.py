import os
import re
import pandas as pd
from tier.environment.api_base import API_base
import hashlib


class RestaurantAPI(API_base):
    def __init__(self, file_path,orders_data_path, discount_data_path = None):
        super().__init__(file_path)
        # Create callable objects with execute attribute
        if not orders_data_path:
            raise ValueError("orders_data_path is required")
        self.orders = self.initialize_csv_data(orders_data_path)
        if discount_data_path:
            self.discounts = self.initialize_csv_data(discount_data_path)
        self.get_menu = self._create_get_menu()
        self.place_order = self._create_place_order()
        self.check_order_status = self._create_check_order_status()
        self.cancel_order = self._create_cancel_order()
        self.get_order_details = self._create_get_order_details()
        self.get_opening_hours = self._create_get_opening_hours()
        
    def _create_get_opening_hours(self):
        class GetOpeningHoursCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self):
                return self.execute()
        
            def execute(self):
                return {
                    "status_code": 200,
                    "opening_hours": self.api.opening_hours
                }
        return GetOpeningHoursCallable(self)
    
    def _create_cancel_order(self):
        class CancelOrderCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)

                if self.api.orders[self.api.orders['Order ID'] == order_id]['Order Status'].item() != "Restaurant Received Order":
                    return self.api.handle_error(f"Order {order_id} is already in preparation, cannot be cancelled", 409)
                
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "order_status": "Order Cancelled"
                }
        
        return CancelOrderCallable(self)

    def _create_check_order_status(self):
        class CheckOrderStatusCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)
                
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "order_status": self.api.orders[self.api.orders['Order ID'] == order_id]['Order Status'].item()
                }
        
        return CheckOrderStatusCallable(self)

    def _create_get_menu(self):
        """Create a callable object for get_menu with execute attribute"""
        class GetMenuCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self):
                return self.execute()
            
            def execute(self):
                menu_df = self.api.df
                return {
                    "status_code": 200,
                    "restaurant": menu_df['Store'].iloc[0],
                    "menu": menu_df[['Item', 'Price']].to_dict('records')
                }
        
        return GetMenuCallable(self)
    
    def _create_place_order(self):
        """Create a callable object for place_order with execute attribute"""
        class PlaceOrderCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                items = params.get("items")
                amounts = params.get("amounts")
                delivery_details = params.get("delivery_details")
                
                expected_params = {"items", "amounts", "delivery_details"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                # discount = params.get("discount")
                # note = params.get("note")
                if not items:
                    return self.api.handle_error("Items are required", 400)
                if not amounts:
                    return self.api.handle_error("Amounts are required", 400)
                if not delivery_details:
                    return self.api.handle_error("Delivery details are required", 400)
                
                if len(items) != len(amounts):
                    return self.api.handle_error("Items and amounts must have the same length", 400)
                
                is_valid, error = self.api.validate_type(items, "items", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(amounts, "amounts", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(delivery_details, "delivery_details", dict)
                if not is_valid:
                    return error

                order_details = []
                order_str = ""
                for item, amount in zip(items, amounts):
                    is_valid, error = self.api.validate_type(item, "item", str)
                    if not is_valid:
                        return error
                    is_valid, error = self.api.validate_type(amount, "amount", int)
                    if not is_valid:
                        return error

                    # Case-insensitive item matching
                    item_lower = item.lower()
                    menu_items_lower = self.api.df['Item'].str.lower()
                    if item_lower not in menu_items_lower.values:
                        return self.api.handle_error(f"Item {item} not found in menu", 404)
                    if amount <= 0:
                        return self.api.handle_error(f"Amount {amount} is not valid", 400)
                    
                    # Get the actual item name from the menu (with original casing)
                    actual_item = self.api.df[menu_items_lower == item_lower]['Item'].item()
                    order_str += f"{actual_item}{amount}"
                    order_details.append({
                        "item": actual_item,
                        "amount": amount,
                        "price": float(self.api.df[menu_items_lower == item_lower]['Price'].item()) * amount
                    })

                order_details.sort(key=lambda x: (x['price'], x['amount'], x['item']))

                for key, value in delivery_details.items():
                    is_valid, error = self.api.validate_type(value, key, str)
                    if not is_valid:
                        return error
                    if key not in ["name", "phone", "address"]:
                        return self.api.handle_error(f"Invalid delivery detail: {key}", 400)
                    if key == "name" and not value:
                        return self.api.handle_error("Name is required", 400)
                    if key == "phone" and not value:
                        return self.api.handle_error("Phone is required", 400)
                    if key == "address" and not value:
                        return self.api.handle_error("Address is required", 400)

                total_amount_for_food = round(sum(order['price'] for order in order_details), 2)

                delivery_cost = 3.99 

                order_id = f"ORD_{hashlib.sha256(order_str.encode()).hexdigest()[:8]}"
                result = {
                    "status_code": 200,
                    "order_id": order_id,
                    "restaurant": self.api.restaurant,
                    "order_details": order_details,
                    "order_for": delivery_details.get("name"),
                    "total_amount_for_food": total_amount_for_food,
                    "delivery_cost": delivery_cost,
                    "total_amount": round(float(total_amount_for_food + delivery_cost), 2)
                }
                return result
        
        return PlaceOrderCallable(self)

    def _create_get_order_details(self):
        class GetOrderDetailsCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)
                
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "restaurant": self.api.orders[self.api.orders['Order ID'] == order_id]['Restaurant'].item(),
                    "order_details": self.api.orders[self.api.orders['Order ID'] == order_id]['Order Details'].item(),
                    "order_for": self.api.orders[self.api.orders['Order ID'] == order_id]['Customer Name'].item(),
                    "total_amount": self.api.orders[self.api.orders['Order ID'] == order_id]['Total Amount'].item()
                }
        return GetOrderDetailsCallable(self)

class McDonalds(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "McDonald's"]
        self.restaurant = "McDonald's"
        self.opening_hours = "24 hours"
class Starbucks(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Starbucks"]
        self.restaurant = "Starbucks"
        self.opening_hours = "4:00 AM - 10:00 PM"

class BBQChicken(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "BBQ Chicken"]
        self.restaurant = "BBQ Chicken"
        self.opening_hours = "11:00 AM - 9:00 PM"

class AABrunch(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "AA Brunch"]
        self.restaurant = "AA Brunch"
        self.opening_hours = "9:30 AM - 2:30 PM"

class BestTeaHouse(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Best Tea House"]
        self.restaurant = "Best Tea House"
        self.opening_hours = "10:00 AM - 10:00 PM"

    def _create_place_order(self):
        """Override to create custom place_order callable"""
        class BestTeaPlaceOrderCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"items", "amounts", "sizes", "delivery_details"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                items = params.get("items")
                amounts = params.get("amounts")
                sizes = params.get("sizes")
                delivery_details = params.get("delivery_details")
                # discount = params.get("discount")
                # note = params.get("note")

                if not len(items) == len(amounts) == len(sizes):
                    return self.api.handle_error("Items, amounts, and sizes must have the same length", 400)
                
                is_valid, error = self.api.validate_type(items, "items", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(amounts, "amounts", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(sizes, "sizes", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(delivery_details, "delivery_details", dict)
                if not is_valid:
                    return error

                order_details = []
                order_str = ""
                for item, amount, size in zip(items, amounts, sizes):
                    is_valid, error = self.api.validate_type(item, "item", str)
                    if not is_valid:
                        return error
                    is_valid, error = self.api.validate_type(amount, "amount", int)
                    if not is_valid:
                        return error
                    is_valid, error = self.api.validate_type(size, "size", str)
                    if not is_valid:
                        return error
                    
                    size = size.lower()
                    if size not in ["m", "l", "large", "medium"]:
                        return self.api.handle_error(f"Size {size} is not valid", 400)
                    
                    # Case-insensitive item matching
                    item_lower = item.lower()
                    menu_items_lower = self.api.df['Item'].str.lower()
                    if item_lower not in menu_items_lower.values:
                        return self.api.handle_error(f"Item {item} not found in menu", 404)
                    if amount <= 0:
                        return self.api.handle_error(f"Amount {amount} is not valid", 400)
                    
                    # Get the actual item name from the menu (with original casing)
                    actual_item = self.api.df[menu_items_lower == item_lower]['Item'].item()
                    order_str += f"{actual_item}{size}{amount}"
                    price = self.api.df[menu_items_lower == item_lower]['Price'].item()
                    if size in ["m", "medium"]:
                        recipt_size = "Medium"
                        price = float(price.split(" / ")[0])
                    elif size in ["l", "large"]:
                        recipt_size = "Large"
                        price = float(price.split(" / ")[1])
                    else:
                        return self.api.handle_error(f"Size {size} is not valid", 400)
                    order_details.append({
                        "item": actual_item,
                        "size": recipt_size,
                        "amount": amount,
                        "price": round(price * amount, 2)
                    })

                order_details.sort(key=lambda x: (x['price'], x['amount'], x['item'], x['size']))

                for key, value in delivery_details.items():
                    is_valid, error = self.api.validate_type(value, key, str)
                    if not is_valid:
                        return error
                    if key not in ["name", "phone", "address"]:
                        return self.api.handle_error(f"Invalid delivery detail: {key}", 400)
                    if key == "name" and not value:
                        return self.api.handle_error("Name is required", 400)
                    if key == "phone" and not value:
                        return self.api.handle_error("Phone is required", 400)
                    if key == "address" and not value:
                        return self.api.handle_error("Address is required", 400)

                total_amount_for_food = sum(order['price'] for order in order_details)

                delivery_cost = 3.99 

                order_id = f"ORD_{hashlib.sha256(order_str.encode()).hexdigest()[:8]}"
                result = {
                    "status_code": 200,
                    "order_id": order_id,
                    "restaurant": self.api.restaurant,
                    "order_details": order_details,
                    "order_for": delivery_details.get("name"),
                    "total_amount_for_food": total_amount_for_food,
                    "delivery_cost": delivery_cost,
                    "total_amount": round(float(total_amount_for_food + delivery_cost), 2)
                }
                return result
        
        return BestTeaPlaceOrderCallable(self)

class TheGoldenSpoon(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "The Golden Spoon"]
        self.restaurant = "The Golden Spoon"
        self.opening_hours = "12:00 PM - 10:00 PM"

class OceanBreezeGrill(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Ocean Breeze Grill"]
        self.restaurant = "Ocean Breeze Grill"
        self.opening_hours = "11:00 AM - 9:00 PM"

class MountainHearthDiner(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Mountain Hearth Diner"]
        self.restaurant = "Mountain Hearth Diner"
        self.opening_hours = "11:00 AM - 1:00 PM, 5:00 PM - 9:00 PM"

class LaPiazzaItaliana(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "La Piazza Italiana"]
        self.restaurant = "La Piazza Italiana"
        self.opening_hours = "5:30 PM - 9:00 PM"
        
class TheRusticTable(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "The Rustic Table"]
        self.restaurant = "The Rustic Table"
        self.opening_hours = "5:00 PM - 9:00 PM"

class BeanAndBrewCoffeehouse(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Bean & Brew Coffeehouse"]
        self.restaurant = "Bean & Brew Coffeehouse"
        self.opening_hours = "6:00 AM - 1:00 PM"

class BobaGalaxy(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Boba Galaxy"]
        self.restaurant = "Boba Galaxy"
        self.opening_hours = "11:00 AM - 9:00 PM"

class FreshSqueezeBar(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Fresh Squeeze Bar"]
        self.restaurant = "Fresh Squeeze Bar"
        self.opening_hours = "11:00 AM - 9:00 PM"

class TokyoDreams(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Tokyo Dreams"]
        self.restaurant = "Tokyo Dreams"
        self.opening_hours = "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM"

class WasabiGarden(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Wasabi Garden"]
        self.restaurant = "Wasabi Garden"
        self.opening_hours = "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM"

class SpiceBazaar(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Spice Bazaar"]
        self.restaurant = "Spice Bazaar"
        self.opening_hours = "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM"

class LuckyDragon(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, discount_data_path = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.df = self.df[self.df['Store'] == "Lucky Dragon"]
        self.restaurant = "Lucky Dragon"
        self.opening_hours = "11:00 AM - 2:00 PM, 5:30 PM - 9:30 PM"
        
class FoodDeliveryAPI(RestaurantAPI):
    def __init__(self, file_path, orders_data_path, supported_restaurants = None, discount_data_path = None, platform = None ):
        super().__init__(file_path, orders_data_path, discount_data_path)
        self.supported_restaurants = supported_restaurants
        self.platform = platform  # Store platform name for automatic injection
        self.df = self.df[self.df['Store'].isin(supported_restaurants)]
        
        # Mapping of restaurant names to their opening hours
        self.restaurant_hours = {
            "McDonald's": "24 hours",
            "Starbucks": "4:00 AM - 10:00 PM",
            "BBQ Chicken": "11:00 AM - 9:00 PM",
            "AA Brunch": "9:30 AM - 2:30 PM",
            "Best Tea House": "10:00 AM - 10:00 PM",
            "The Golden Spoon": "12:00 PM - 10:00 PM",
            "Ocean Breeze Grill": "11:00 AM - 9:00 PM",
            "Mountain Hearth Diner": "11:00 AM - 1:00 PM, 5:00 PM - 9:00 PM",
            "La Piazza Italiana": "5:30 PM - 9:00 PM",
            "The Rustic Table": "5:00 PM - 9:00 PM",
            "Bean & Brew Coffeehouse": "6:00 AM - 1:00 PM",
            "Boba Galaxy": "11:00 AM - 9:00 PM",
            "Fresh Squeeze Bar": "11:00 AM - 9:00 PM",
            "Tokyo Dreams": "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM",
            "Wasabi Garden": "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM",
            "Spice Bazaar": "11:00 AM - 1:00 PM, 4:30 PM - 8:30 PM",
            "Lucky Dragon": "11:00 AM - 2:00 PM, 5:30 PM - 9:30 PM"
        }

        self.list_restaurants = self._create_list_restaurants()
        self.get_menu = self._create_get_menu()
        self.place_order = self._create_place_order()
        self.cancel_order = self._create_cancel_order()
        self.check_order_status = self._create_check_order_status()
        self.get_order_details = self._create_get_order_details()
        self.get_opening_hours = self._create_get_opening_hours()

    def _create_cancel_order(self):
        class CancelOrderCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)
                
                order_row = self.api.orders[self.api.orders['Order ID'] == order_id]
                if not order_row.empty:
                    if order_row['Platform'].item() != self.api.platform:
                        return self.api.handle_error(f"Order {order_id} is not from {self.api.platform}", 400)
                    if order_row['Order Status'].item() != "Restaurant Received Order":
                        return self.api.handle_error(f"Order {order_id} is already in preparation, cannot be cancelled", 409)
                    
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "order_status": "Order Cancelled"
                }
        return CancelOrderCallable(self)
    
    def _create_get_opening_hours(self):
        class GetOpeningHoursCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
        
            def execute(self, **params):
                expected_params = {"restaurant"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                restaurant = params.get("restaurant")
                if not restaurant:
                    return self.api.handle_error("Restaurant is required", 400)
                
                is_valid, error = self.api.validate_type(restaurant, "restaurant", str)
                if not is_valid:
                    return error
                    
                if restaurant not in self.api.supported_restaurants:
                    return self.api.handle_error(f"Restaurant {restaurant} not supported by this delivery service", 404)
                
                opening_hours = self.api.restaurant_hours.get(restaurant)
                if not opening_hours:
                    return self.api.handle_error(f"Opening hours not available for {restaurant}", 404)
                    
                return {
                    "status_code": 200,
                    "restaurant": restaurant,
                    "opening_hours": opening_hours
                }
        return GetOpeningHoursCallable(self)
    
    def _create_list_restaurants(self):
        class ListRestaurantsCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self):
                return self.execute()
            
            def execute(self):
                return {
                    "status_code": 200,
                    "restaurants": self.api.supported_restaurants
                }
        return ListRestaurantsCallable(self)

    def _create_get_menu(self, **params):
        class GetMenuCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"restaurant"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                restaurant = params.get("restaurant")
                if not restaurant:
                    return self.api.handle_error("Restaurant is required", 400)
                if restaurant not in self.api.supported_restaurants:
                    return self.api.handle_error(f"Restaurant {restaurant} not supported by this delivery service", 404)
                return {
                    "status_code": 200,
                    "restaurant": restaurant,
                    "menu": self.api.df[self.api.df['Store'] == restaurant][['Item', 'Price']].to_dict('records')
                }
        return GetMenuCallable(self)
    
    def _create_place_order(self):
        """Create a callable object for place_order with execute attribute"""
        class PlaceOrderCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"restaurant", "items", "amounts", "delivery_details"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                platform = self.api.platform
                restaurant = params.get("restaurant")
                items = params.get("items")
                amounts = params.get("amounts")
                delivery_details = params.get("delivery_details")
                # discount = params.get("discount")
                # note = params.get("note")

                if not restaurant:
                    return self.api.handle_error("Restaurant is required", 400)
                if restaurant not in self.api.supported_restaurants:
                    return self.api.handle_error(f"Restaurant {restaurant} not supported by this delivery service", 404)  
                if not items:
                    return self.api.handle_error("Items are required", 400)
                if not amounts:
                    return self.api.handle_error("Amounts are required", 400)
                if not delivery_details:
                    return self.api.handle_error("Delivery details are required", 400)
                
                if len(items) != len(amounts):
                    return self.api.handle_error("Items and amounts must have the same length", 400)
                
                is_valid, error = self.api.validate_type(items, "items", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(amounts, "amounts", list)
                if not is_valid:
                    return error
                is_valid, error = self.api.validate_type(delivery_details, "delivery_details", dict)
                if not is_valid:
                    return error

                restaurant_df = self.api.df[self.api.df['Store'] == restaurant]
                order_details = []
                order_str = ""
                for item, amount in zip(items, amounts):
                    is_valid, error = self.api.validate_type(item, "item", str)
                    if not is_valid:
                        return error
                    is_valid, error = self.api.validate_type(amount, "amount", int)
                    if not is_valid:
                        return error

                    # Case-insensitive item matching
                    item_lower = item.lower()
                    menu_items_lower = restaurant_df['Item'].str.lower()
                    if item_lower not in menu_items_lower.values:
                        return self.api.handle_error(f"Item {item} not found in menu", 404)
                    if amount <= 0:
                        return self.api.handle_error(f"Amount {amount} is not valid", 400)
                    
                    # Get the actual item name from the menu (with original casing)
                    actual_item = restaurant_df[menu_items_lower == item_lower]['Item'].item()
                    order_str += f"{actual_item}{amount}"
                    order_details.append({
                        "item": actual_item,
                        "amount": amount,
                        "price": float(restaurant_df[menu_items_lower == item_lower]['Price'].item()) * amount
                    })

                order_details.sort(key=lambda x: (x['price'], x['amount'], x['item']))

                for key, value in delivery_details.items():
                    is_valid, error = self.api.validate_type(value, key, str)
                    if not is_valid:
                        return error
                    if key not in ["name", "phone", "address"]:
                        return self.api.handle_error(f"Invalid delivery detail: {key}", 400)
                    if key == "name" and not value:
                        return self.api.handle_error("Name is required", 400)
                    if key == "phone" and not value:
                        return self.api.handle_error("Phone is required", 400)
                    if key == "address" and not value:
                        return self.api.handle_error("Address is required", 400)

                total_amount_for_food = round(sum(order['price'] for order in order_details), 2)

                delivery_cost = 3.99 
                if platform == "UberEats":
                    platform_handling_fee = 3.00
                elif platform == "Doordash":
                    platform_handling_fee = 2.50
                elif platform == "Grubhub":
                    platform_handling_fee = 2.00

                order_id = f"ORD_{hashlib.sha256((platform+order_str).encode()).hexdigest()[:8]}"
                result = {
                    "status_code": 200,
                    "order_id": order_id,
                    "restaurant": restaurant,
                    "order_details": order_details,
                    "order_for": delivery_details.get("name"),
                    "total_amount_for_food": total_amount_for_food,
                    "delivery_cost": delivery_cost,
                    "platform_handling_fee": platform_handling_fee,
                    "total_amount": round(float(total_amount_for_food + delivery_cost + platform_handling_fee), 2)
                }
                return result
        
        return PlaceOrderCallable(self)
    
    def _create_check_order_status(self):
        class CheckOrderStatusCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)
                
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "platform": self.api.platform,
                    "restaurant": self.api.orders[self.api.orders['Order ID'] == order_id]['Restaurant'].item(),
                    "order_status": self.api.orders[self.api.orders['Order ID'] == order_id]['Order Status'].item()
                }
        
        return CheckOrderStatusCallable(self)

    def _create_get_order_details(self):
        class GetOrderDetailsCallable:
            def __init__(self, api):
                self.api = api
            
            def __call__(self, **params):
                return self.execute(**params)
            
            def execute(self, **params):
                expected_params = {"order_id"}
                unexpected_params = set(params.keys()) - expected_params
                if unexpected_params:
                    return self.api.handle_error(f"Unexpected parameters: {', '.join(unexpected_params)}", 400)
                
                order_id = params.get("order_id")
                if not order_id:
                    return self.api.handle_error("Order ID is required", 400)
                
                is_valid, error = self.api.validate_type(order_id, "order_id", str)
                if not is_valid:
                    return error
                if order_id not in self.api.orders['Order ID'].values:
                    return self.api.handle_error(f"Order ID {order_id} not found", 404)
                
                return {
                    "status_code": 200,
                    "order_id": order_id,
                    "platform": self.api.platform,
                    "restaurant": self.api.orders[self.api.orders['Order ID'] == order_id]['Restaurant'].item(),
                    "order_details": self.api.orders[self.api.orders['Order ID'] == order_id]['Order Details'].item(),
                    "order_for": self.api.orders[self.api.orders['Order ID'] == order_id]['Customer Name'].item(),
                    "total_amount": self.api.orders[self.api.orders['Order ID'] == order_id]['Total Amount'].item()
                }
        return GetOrderDetailsCallable(self)

class UberEats(FoodDeliveryAPI):
    def __init__(self, file_path, orders_data_path, supported_restaurants = None, discount_data_path = None ):
        self.platform = "UberEats"
        if supported_restaurants is None:
            supported_restaurants = ['La Piazza Italiana', 'Lucky Dragon', 'Boba Galaxy', 'Wasabi Garden', 'Fresh Squeeze Bar', 'Starbucks', 'AA Brunch', 'Tokyo Dreams', 'The Rustic Table', 'BBQ Chicken']
        super().__init__(file_path, orders_data_path, supported_restaurants, discount_data_path, platform="UberEats")
        self.df = self.df[self.df['Store'].isin(supported_restaurants)]
        

class Doordash(FoodDeliveryAPI):
    def __init__(self, file_path, orders_data_path, supported_restaurants = None, discount_data_path = None ):
        self.platform = "Doordash"
        if supported_restaurants is None:
            supported_restaurants = ['The Rustic Table', 'Spice Bazaar', 'Boba Galaxy', 'Mountain Hearth Diner', 'Lucky Dragon', 'Starbucks', 'Ocean Breeze Grill', 'The Golden Spoon', 'Bean & Brew Coffeehouse', 'Fresh Squeeze Bar']
        super().__init__(file_path, orders_data_path, supported_restaurants, discount_data_path, platform="Doordash")
        self.df = self.df[self.df['Store'].isin(supported_restaurants)]
        

class Grubhub(FoodDeliveryAPI):
    def __init__(self, file_path, orders_data_path, supported_restaurants = None, discount_data_path = None ):
        self.platform = "Grubhub"
        if supported_restaurants is None:
            supported_restaurants = ['BBQ Chicken', 'Best Tea House', 'Tokyo Dreams', "McDonald's", 'The Rustic Table', 'Starbucks', 'Ocean Breeze Grill', 'Fresh Squeeze Bar', 'Spice Bazaar', 'Wasabi Garden']
        super().__init__(file_path, orders_data_path, supported_restaurants, discount_data_path, platform="Grubhub")
        self.df = self.df[self.df['Store'].isin(supported_restaurants)]
