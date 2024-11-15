#!/usr/bin/env python3
"""Food Delivery Simulator

A terminal-based app that simulates ordering food online.

Features:
    * Browse a menu organised by category
    * Add, remove, and change items in a cart
    * Apply promo codes and see a full price breakdown
    * Check out with delivery details and a payment method
    * Track delivery status live, or look up past orders

Run it with:
    python3 food_delivery_simulator.py
    python3 food_delivery_simulator.py --speed 10   # 10x faster deliveries

Only the Python standard library is used (Python 3.9+).
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CURRENCY = "$"
TAX_RATE = 0.075
DELIVERY_FEE = 2.99
FREE_DELIVERY_THRESHOLD = 40.00
PAYMENT_METHODS = ["Card", "Cash on delivery", "Wallet"]

# Promo code -> fraction taken off the subtotal.
PROMO_CODES: Dict[str, float] = {
    "WELCOME10": 0.10,
    "SAVE20": 0.20,
}

DRIVER_NAMES = ["Ada", "Marcus", "Priya", "Tomas", "Lena", "Samir", "Joy", "Kofi"]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MenuItem:
    """A single item that can be ordered."""

    item_id: int
    name: str
    price: float
    category: str


MENU: List[MenuItem] = [
    MenuItem(1, "Margherita Pizza", 11.50, "Mains"),
    MenuItem(2, "Spicy Chicken Burger", 9.75, "Mains"),
    MenuItem(3, "Jollof Rice with Chicken", 12.00, "Mains"),
    MenuItem(4, "Veggie Pasta", 10.25, "Mains"),
    MenuItem(5, "Garlic Bread", 4.50, "Sides"),
    MenuItem(6, "Loaded Fries", 5.75, "Sides"),
    MenuItem(7, "Coleslaw", 3.25, "Sides"),
    MenuItem(8, "Lemonade", 2.75, "Drinks"),
    MenuItem(9, "Iced Tea", 2.50, "Drinks"),
    MenuItem(10, "Sparkling Water", 1.95, "Drinks"),
    MenuItem(11, "Chocolate Brownie", 4.25, "Desserts"),
    MenuItem(12, "Vanilla Ice Cream", 3.75, "Desserts"),
]

MENU_BY_ID: Dict[int, MenuItem] = {item.item_id: item for item in MENU}


class OrderStatus(Enum):
    """The stages an order moves through."""

    CONFIRMED = "Order confirmed"
    PREPARING = "Kitchen is preparing your food"
    OUT_FOR_DELIVERY = "Driver is on the way"
    DELIVERED = "Delivered. Enjoy your meal!"


# (status, seconds spent in that stage at normal speed)
STAGES = [
    (OrderStatus.CONFIRMED, 8),
    (OrderStatus.PREPARING, 25),
    (OrderStatus.OUT_FOR_DELIVERY, 40),
]
TOTAL_DELIVERY_SECONDS = sum(seconds for _, seconds in STAGES)


@dataclass
class Totals:
    """A full price breakdown for a cart."""

    subtotal: float
    discount: float
    tax: float
    delivery_fee: float

    @property
    def total(self) -> float:
        return round(self.subtotal - self.discount + self.tax + self.delivery_fee, 2)


class Cart:
    """Holds the items a customer wants to order."""

    def __init__(self) -> None:
        self._items: Dict[int, int] = {}  # item_id -> quantity
        self.promo_code: Optional[str] = None

    def add(self, item: MenuItem, quantity: int = 1) -> None:
        self._items[item.item_id] = self._items.get(item.item_id, 0) + quantity

    def set_quantity(self, item_id: int, quantity: int) -> None:
        """Set an item's quantity. A quantity of 0 removes it."""
        if quantity <= 0:
            self._items.pop(item_id, None)
        else:
            self._items[item_id] = quantity

    def clear(self) -> None:
        self._items.clear()
        self.promo_code = None

    def is_empty(self) -> bool:
        return not self._items

    def lines(self) -> List[tuple]:
        """Return (MenuItem, quantity) pairs in menu order."""
        return [(MENU_BY_ID[i], q) for i, q in sorted(self._items.items())]

    def item_count(self) -> int:
        return sum(self._items.values())

    def totals(self) -> Totals:
        subtotal = sum(item.price * qty for item, qty in self.lines())
        rate = PROMO_CODES.get(self.promo_code or "", 0.0)
        discount = round(subtotal * rate, 2)
        tax = round((subtotal - discount) * TAX_RATE, 2)
        fee = 0.0 if subtotal >= FREE_DELIVERY_THRESHOLD or subtotal == 0 else DELIVERY_FEE
        return Totals(round(subtotal, 2), discount, tax, fee)


@dataclass
class Order:
    """A placed order whose status changes as time passes."""

    order_id: str
    customer: str
    address: str
    payment: str
    lines: List[tuple]
    totals: Totals
    driver: str
    speed: float = 1.0
    placed_at: float = field(default_factory=time.monotonic)

    def elapsed(self) -> float:
        """Simulated seconds since the order was placed."""
        return (time.monotonic() - self.placed_at) * self.speed

    def progress(self) -> float:
        """Fraction of the delivery that is complete, from 0.0 to 1.0."""
        return min(self.elapsed() / TOTAL_DELIVERY_SECONDS, 1.0)

    def status(self) -> OrderStatus:
        elapsed = self.elapsed()
        boundary = 0.0
        for stage_status, seconds in STAGES:
            boundary += seconds
            if elapsed < boundary:
                return stage_status
        return OrderStatus.DELIVERED

    def eta_seconds(self) -> int:
        remaining = max(TOTAL_DELIVERY_SECONDS - self.elapsed(), 0)
        return int(remaining / self.speed)


# ---------------------------------------------------------------------------
# Input / output helpers
# ---------------------------------------------------------------------------

def money(amount: float) -> str:
    return f"{CURRENCY}{amount:,.2f}"


def heading(text: str) -> None:
    print("\n" + "=" * 44)
    print(f"  {text}")
    print("=" * 44)


def ask_int(prompt: str, low: int, high: int) -> int:
    """Keep asking until the user enters a whole number in [low, high]."""
    while True:
        raw = input(prompt).strip()
        if raw.lstrip("-").isdigit() and low <= int(raw) <= high:
            return int(raw)
        print(f"  Please enter a number from {low} to {high}.")


def ask_text(prompt: str, min_length: int = 2) -> str:
    """Keep asking until the user enters non-trivial text."""
    while True:
        raw = input(prompt).strip()
        if len(raw) >= min_length:
            return raw
        print(f"  Please enter at least {min_length} characters.")


def ask_yes_no(prompt: str) -> bool:
    while True:
        raw = input(f"{prompt} (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer y or n.")


def print_cart(cart: Cart) -> None:
    heading("YOUR CART")
    if cart.is_empty():
        print("  Your cart is empty.")
        return
    for index, (item, qty) in enumerate(cart.lines(), start=1):
        print(f"  {index}. {item.name:<26} x{qty:<3} {money(item.price * qty):>9}")
    print_totals(cart.totals(), cart.promo_code)


def print_totals(totals: Totals, promo: Optional[str]) -> None:
    print("  " + "-" * 42)
    print(f"  {'Subtotal':<32}{money(totals.subtotal):>10}")
    if totals.discount:
        label = f"Discount ({promo})"
        print(f"  {label:<32}{'-' + money(totals.discount):>10}")
    print(f"  {'Tax':<32}{money(totals.tax):>10}")
    fee = money(totals.delivery_fee) if totals.delivery_fee else "FREE"
    print(f"  {'Delivery':<32}{fee:>10}")
    print(f"  {'TOTAL':<32}{money(totals.total):>10}")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class FoodDeliveryApp:
    """Ties the menus, cart, and orders together."""

    def __init__(self, speed: float = 1.0) -> None:
        self.cart = Cart()
        self.orders: List[Order] = []
        self.speed = speed
        self._next_order_number = 1001

    # -- browsing ----------------------------------------------------------

    def browse_menu(self) -> None:
        categories = sorted({item.category for item in MENU})
        while True:
            heading("MENU CATEGORIES")
            for number, name in enumerate(categories, start=1):
                print(f"  {number}. {name}")
            print("  0. Back")
            choice = ask_int("Choose a category: ", 0, len(categories))
            if choice == 0:
                return
            self._browse_category(categories[choice - 1])

    def _browse_category(self, category: str) -> None:
        items = [item for item in MENU if item.category == category]
        while True:
            heading(category.upper())
            for number, item in enumerate(items, start=1):
                print(f"  {number}. {item.name:<26} {money(item.price):>8}")
            print("  0. Back")
            choice = ask_int("Add which item? ", 0, len(items))
            if choice == 0:
                return
            item = items[choice - 1]
            quantity = ask_int(f"How many {item.name}? (1-20): ", 1, 20)
            self.cart.add(item, quantity)
            print(f"  Added {quantity} x {item.name}. "
                  f"Cart now has {self.cart.item_count()} item(s).")

    # -- cart --------------------------------------------------------------

    def manage_cart(self) -> None:
        while True:
            print_cart(self.cart)
            if self.cart.is_empty():
                return
            print("\n  1. Change quantity   2. Remove item")
            print("  3. Apply promo code  4. Clear cart   0. Back")
            choice = ask_int("Choose an option: ", 0, 4)
            if choice == 0:
                return
            if choice == 1:
                self._change_quantity()
            elif choice == 2:
                self._remove_item()
            elif choice == 3:
                self._apply_promo()
            elif choice == 4 and ask_yes_no("Clear the whole cart?"):
                self.cart.clear()

    def _pick_cart_line(self, prompt: str) -> Optional[MenuItem]:
        lines = self.cart.lines()
        number = ask_int(prompt, 1, len(lines))
        return lines[number - 1][0]

    def _change_quantity(self) -> None:
        item = self._pick_cart_line("Line number to change: ")
        quantity = ask_int(f"New quantity for {item.name} (0 removes it): ", 0, 20)
        self.cart.set_quantity(item.item_id, quantity)

    def _remove_item(self) -> None:
        item = self._pick_cart_line("Line number to remove: ")
        self.cart.set_quantity(item.item_id, 0)
        print(f"  Removed {item.name}.")

    def _apply_promo(self) -> None:
        code = input("Enter promo code: ").strip().upper()
        if code in PROMO_CODES:
            self.cart.promo_code = code
            print(f"  Promo {code} applied: {int(PROMO_CODES[code] * 100)}% off.")
        else:
            print("  That promo code is not valid.")

    # -- checkout ----------------------------------------------------------

    def checkout(self) -> None:
        if self.cart.is_empty():
            print("\n  Your cart is empty. Add something from the menu first.")
            return

        print_cart(self.cart)
        heading("CHECKOUT")
        name = ask_text("Your name: ")
        address = ask_text("Delivery address: ", min_length=5)

        print("\nPayment method:")
        for number, method in enumerate(PAYMENT_METHODS, start=1):
            print(f"  {number}. {method}")
        payment = PAYMENT_METHODS[ask_int("Choose a method: ", 1, len(PAYMENT_METHODS)) - 1]

        print(f"\n  Deliver to {name}, {address}")
        print(f"  Pay by: {payment}")
        print_totals(self.cart.totals(), self.cart.promo_code)
        if not ask_yes_no("Place this order?"):
            print("  Order not placed. Your cart is unchanged.")
            return

        order = Order(
            order_id=f"FD-{self._next_order_number}",
            customer=name,
            address=address,
            payment=payment,
            lines=self.cart.lines(),
            totals=self.cart.totals(),
            driver=random.choice(DRIVER_NAMES),
            speed=self.speed,
        )
        self._next_order_number += 1
        self.orders.append(order)
        self.cart.clear()

        print(f"\n  Order {order.order_id} placed. Thank you, {name}!")
        if ask_yes_no("Watch the delivery live now?"):
            self.watch_order(order)

    # -- tracking ----------------------------------------------------------

    def track_orders(self) -> None:
        if not self.orders:
            print("\n  You have no orders yet.")
            return
        while True:
            heading("YOUR ORDERS")
            for number, order in enumerate(self.orders, start=1):
                print(f"  {number}. {order.order_id}  {money(order.totals.total):>9}  "
                      f"{order.status().value}")
            print("  0. Back")
            choice = ask_int("Open which order? ", 0, len(self.orders))
            if choice == 0:
                return
            self._order_details(self.orders[choice - 1])

    def _order_details(self, order: Order) -> None:
        heading(f"ORDER {order.order_id}")
        print(f"  Customer: {order.customer}")
        print(f"  Address:  {order.address}")
        print(f"  Payment:  {order.payment}")
        print(f"  Driver:   {order.driver}")
        for item, qty in order.lines:
            print(f"    {qty} x {item.name}")
        print_totals(order.totals, None if not order.totals.discount else "promo")
        print(f"\n  Status: {order.status().value}")
        if order.status() is not OrderStatus.DELIVERED:
            if ask_yes_no("Watch this order live?"):
                self.watch_order(order)

    def watch_order(self, order: Order) -> None:
        """Show a live progress bar until delivery. Ctrl+C stops watching."""
        print(f"\n  Tracking {order.order_id} (press Ctrl+C to stop watching)\n")
        last_status: Optional[OrderStatus] = None
        try:
            while True:
                status = order.status()
                if status is not last_status:
                    if last_status is not None:
                        print()
                    note = ""
                    if status is OrderStatus.OUT_FOR_DELIVERY:
                        note = f" ({order.driver})"
                    print(f"  >> {status.value}{note}")
                    last_status = status

                filled = int(order.progress() * 30)
                bar = "#" * filled + "." * (30 - filled)
                eta = f"ETA {order.eta_seconds()}s" if status is not OrderStatus.DELIVERED else "Done"
                sys.stdout.write(f"\r  [{bar}] {int(order.progress() * 100):>3}%  {eta}   ")
                sys.stdout.flush()

                if status is OrderStatus.DELIVERED:
                    print()
                    return
                time.sleep(0.4)
        except KeyboardInterrupt:
            print("\n  Stopped watching. The order keeps going in the background.")

    # -- main loop ---------------------------------------------------------

    def run(self) -> None:
        heading("FOOD DELIVERY SIMULATOR")
        while True:
            cart_note = f" ({self.cart.item_count()})" if not self.cart.is_empty() else ""
            print("\nMAIN MENU")
            print("  1. Browse menu")
            print(f"  2. View cart{cart_note}")
            print("  3. Checkout")
            print("  4. Track orders")
            print("  0. Quit")
            choice = ask_int("Choose an option: ", 0, 4)
            if choice == 1:
                self.browse_menu()
            elif choice == 2:
                self.manage_cart()
            elif choice == 3:
                self.checkout()
            elif choice == 4:
                self.track_orders()
            else:
                print("\nThanks for using Food Delivery Simulator. Goodbye!")
                return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminal food delivery simulator.")
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Delivery speed multiplier (default 1.0, try 10 for a quick demo).",
    )
    args = parser.parse_args()
    if args.speed <= 0:
        parser.error("--speed must be greater than 0")
    return args


def main() -> None:
    args = parse_args()
    app = FoodDeliveryApp(speed=args.speed)
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSession ended. Goodbye!")


if __name__ == "__main__":
    main()
