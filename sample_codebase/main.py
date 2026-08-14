from utils.math_ops import calculate_discount, compute_tax

class OrderProcessor:
    def __init__(self, order_id, user_name):
        self.order_id = order_id
        self.user_name = user_name
        self.items = []

    def add_item(self, item_name, price):
        self.items.append({"name": item_name, "price": price})

    def process_order(self, discount_percent=0, state_code="CA"):
        subtotal = sum(item["price"] for item in self.items)
        discounted_price = calculate_discount(subtotal, discount_percent)
        tax = compute_tax(discounted_price, state_code)
        total = discounted_price + tax
        return {
            "order_id": self.order_id,
            "subtotal": subtotal,
            "discounted_price": discounted_price,
            "tax": tax,
            "total": total
        }

if __name__ == "__main__":
    processor = OrderProcessor(101, "Alice")
    processor.add_item("Laptop", 1200.0)
    processor.add_item("Mouse", 25.0)
    result = processor.process_order(10, "CA")
    print(f"Order Result: {result}")
