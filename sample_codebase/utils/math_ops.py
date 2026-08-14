# Legacy Math Operations Module

def calculate_discount(price, discount_percent):
    """Calculates final price after applying discount percentage."""
    if price < 0 or discount_percent < 0:
        raise ValueError("Price and discount must be non-negative")
    discount_amount = price * (discount_percent / 100.0)
    return round(price - discount_amount, 2)

def compute_tax(price, state_code):
    """Legacy tax calculator for US states."""
    tax_rates = {
        "CA": 0.0725,
        "NY": 0.04,
        "TX": 0.0625,
        "FL": 0.06
    }
    rate = tax_rates.get(state_code.upper(), 0.05)
    return round(price * rate, 2)
