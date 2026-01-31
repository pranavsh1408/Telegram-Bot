"""
API Monitor for PhonePe Voucher availability on StanShop.
Fetches inventory data and tracks denomination availability.
"""

import requests
from datetime import datetime
from config import STANSHOP_API_URL, STANSHOP_PRODUCT_URL


# Store previous state to detect changes
_previous_denominations = None
_last_check_time = None


def fetch_inventory():
    """
    Fetch inventory data from StanShop API.
    
    Returns:
        dict: API response data or None if request fails
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        response = requests.get(STANSHOP_API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching inventory: {e}")
        return None


def parse_denominations(data):
    """
    Extract denomination information from API response.
    
    Args:
        data: API response dictionary
        
    Returns:
        list: List of denomination dictionaries with value and price info
    """
    if not data:
        return []
    
    try:
        inventory = data.get("inventory", {})
        denominations = inventory.get("stanValueDenomination", [])
        return denominations if denominations else []
    except (KeyError, TypeError):
        return []


def check_availability():
    """
    Check current voucher availability.
    
    Returns:
        dict: Status information including:
            - available: bool indicating if vouchers are in stock
            - denominations: list of available denominations
            - message: Human-readable status message
            - check_time: Timestamp of this check
    """
    global _last_check_time
    
    _last_check_time = datetime.now()
    
    data = fetch_inventory()
    if data is None:
        return {
            "available": False,
            "denominations": [],
            "message": "❌ Failed to fetch data from StanShop API",
            "check_time": _last_check_time,
            "error": True
        }
    
    denominations = parse_denominations(data)
    
    if denominations:
        # Format denomination details
        denom_text = format_denominations(denominations)
        return {
            "available": True,
            "denominations": denominations,
            "message": f"🎉 *PhonePe Vouchers Available!*\n\n{denom_text}\n\n🔗 [Buy Now]({STANSHOP_PRODUCT_URL})",
            "check_time": _last_check_time,
            "error": False
        }
    else:
        return {
            "available": False,
            "denominations": [],
            "message": "📭 No PhonePe vouchers currently available",
            "check_time": _last_check_time,
            "error": False
        }


def format_denominations(denominations):
    """
    Format denomination list for display.
    
    Args:
        denominations: List of denomination objects
        
    Returns:
        str: Formatted string with denomination details
    """
    if not denominations:
        return "No denominations available"
    
    lines = ["*Available Denominations:*\n"]
    
    for denom in denominations:
        # Handle different possible data structures
        if isinstance(denom, dict):
            value = denom.get("value", denom.get("denomination", "Unknown"))
            price = denom.get("price", denom.get("sellingPrice", ""))
            discount = denom.get("discount", "")
            
            line = f"💰 ₹{value}"
            if price:
                line += f" - Price: ₹{price}"
            if discount:
                line += f" ({discount}% OFF)"
            lines.append(line)
        else:
            # If it's just a value
            lines.append(f"💰 ₹{denom}")
    
    return "\n".join(lines)


def check_for_stock_change():
    """
    Check if stock status has changed from unavailable to available.
    Used for notifications - only alerts when stock appears.
    
    Returns:
        dict: Contains 'changed' bool and full status info
    """
    global _previous_denominations
    
    status = check_availability()
    
    if status.get("error"):
        return {"changed": False, "status": status, "reason": "api_error"}
    
    current_available = status["available"]
    previous_available = _previous_denominations is not None and len(_previous_denominations) > 0
    
    # Detect change: was unavailable, now available
    stock_appeared = current_available and not previous_available
    
    # Update previous state
    _previous_denominations = status["denominations"]
    
    return {
        "changed": stock_appeared,
        "status": status,
        "reason": "stock_appeared" if stock_appeared else "no_change"
    }


def get_last_check_time():
    """Get the timestamp of the last check."""
    return _last_check_time


def reset_tracking():
    """Reset tracking state (useful for testing)."""
    global _previous_denominations, _last_check_time
    _previous_denominations = None
    _last_check_time = None


if __name__ == "__main__":
    # Test the monitor
    print("Testing PhonePe Voucher Monitor...")
    print("-" * 40)
    
    status = check_availability()
    print(f"Check Time: {status['check_time']}")
    print(f"Available: {status['available']}")
    print(f"Denominations: {status['denominations']}")
    print(f"\nMessage:\n{status['message']}")
