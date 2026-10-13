"""In-memory domain models for menu items, orders, stock, and sales."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Business logic for menu and order handling in the restaurant system.


@dataclass
class MenuItem:
    # Represents a single dish or product available in the restaurant menu.
    name: str
    price: float
    category: str
    stock: int = 0

    def __post_init__(self):
        # Prevent invalid menu configuration.
        normalized_name = (self.name or "").strip()
        if not normalized_name:
            raise ValueError("Item name is required.")
        self.name = normalized_name

        if self.price is None:
            raise ValueError("Price is required.")
        try:
            self.price = float(self.price)
        except (TypeError, ValueError):
            raise ValueError("Price must be a valid number.") from None

        if self.price < 0:
            raise ValueError("Price cannot be negative.")

        if self.stock is None:
            raise ValueError("Stock is required.")
        try:
            self.stock = int(self.stock)
        except (TypeError, ValueError):
            raise ValueError("Stock must be a valid number.") from None

        if self.stock < 0:
            raise ValueError("Stock cannot be negative.")


@dataclass
class OrderItem:
    # Each item inside a customer order contains a product name, quantity, and unit price.
    name: str
    quantity: int
    unit_price: float

    @property
    def total(self) -> float:
        # The line total for a single ordered product.
        return self.quantity * self.unit_price


@dataclass
class Order:
    # Holds order lines and resolves item prices from the attached menu.
    items: List[OrderItem] = field(default_factory=list)
    menu: List[MenuItem] = field(default_factory=list)

    def add_item(self, item_name: str, quantity: int, unit_price: float = 0.0) -> None:
        normalized_name = (item_name or "").strip()
        if not normalized_name:
            raise ValueError("Item name is required.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if unit_price is None:
            unit_price = 0.0
        try:
            unit_price = float(unit_price)
        except (TypeError, ValueError):
            raise ValueError("Unit price must be a valid number.") from None

        if unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

        if unit_price == 0.0:
            for menu_item in self.menu:
                if menu_item.name.lower() == normalized_name.lower():
                    unit_price = menu_item.price
                    break

        self.items.append(OrderItem(normalized_name, quantity, unit_price))

    @property
    def total(self) -> float:
        total = 0.0
        for item in self.items:
            if item.unit_price == 0.0:
                for menu_item in self.menu:
                    if menu_item.name.lower() == item.name.lower():
                        item.unit_price = menu_item.price
                        break
            total += item.total
        return total


class RestaurantManagementSystem:
    # Main controller for menu updates, order creation, and sales tracking.
    def __init__(self):
        self.menu: List[MenuItem] = []
        self.sales: float = 0.0

    def add_menu_item(self, item_or_name, price=None, category="General", stock=0):
        # Add either a MenuItem object or a new item built from basic values.
        if isinstance(item_or_name, MenuItem):
            item = item_or_name
        else:
            item_name = (item_or_name or "").strip()
            if not item_name:
                raise ValueError("Item name is required.")
            item = MenuItem(name=item_name, price=price, category=category, stock=stock)

        if any(existing.name.lower() == item.name.lower() for existing in self.menu):
            raise ValueError(f"Menu item '{item.name}' already exists.")

        self.menu.append(item)
        return item

    def get_menu_item(self, name: str) -> Optional[MenuItem]:
        for item in self.menu:
            if item.name.lower() == name.lower():
                return item
        return None

    def create_order(self) -> Order:
        return Order(menu=self.menu)

    def process_order(self, order: Order) -> float:
        # Validate stock availability and update inventory before adding to sales.
        total = 0.0
        for order_item in order.items:
            menu_item = self.get_menu_item(order_item.name)
            if menu_item is None:
                raise ValueError(f"No menu item found for '{order_item.name}'.")
            if order_item.quantity > menu_item.stock:
                raise ValueError(f"Not enough stock for '{menu_item.name}'.")

            if order_item.unit_price == 0.0:
                order_item.unit_price = menu_item.price

            total += order_item.total
            menu_item.stock -= order_item.quantity

        self.sales += total
        return total

    def list_menu(self) -> List[MenuItem]:
        return self.menu

    def view_sales(self) -> float:
        return self.sales
