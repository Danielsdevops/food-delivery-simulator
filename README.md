# Food Delivery Simulator

A terminal-based Python app that simulates ordering food online. Browse a menu, build a cart, check out, and watch your order move from the kitchen to your door with a live progress bar.

It uses only the Python standard library, so there is nothing to install.

## Features

- Menu organised into categories (Mains, Sides, Drinks, Desserts)
- Cart management: add items, change quantities, remove items, clear the cart
- Promo codes with a full price breakdown (subtotal, discount, tax, delivery fee)
- Free delivery above a spending threshold
- Checkout with name, address, and payment method
- Live delivery tracking through four stages: confirmed, preparing, out for delivery, delivered
- Order history, so you can place several orders and check on each one
- Input validation on every prompt, so bad input never crashes the app

## Requirements

- Python 3.9 or newer

Check your version with:

```bash
python3 --version
```

## How to run

```bash
python3 food_delivery_simulator.py
```

A full delivery takes about 73 seconds. For a quicker demo, use the speed flag:

```bash
python3 food_delivery_simulator.py --speed 10
```

## How it works

| Piece | What it does |
|-------|--------------|
| `MenuItem` | Immutable dataclass describing one dish |
| `Cart` | Stores item quantities and calculates totals, including promo discounts |
| `Totals` | Dataclass holding the price breakdown |
| `Order` | A placed order. Its status is computed from elapsed time, so it keeps progressing even while you browse other menus |
| `FoodDeliveryApp` | Runs the menus, checkout flow, and tracking screens |

Delivery progress is time-based. Each order records when it was placed and works out its current stage from the time that has passed, scaled by the `--speed` value.

## Try these

- Promo codes: `WELCOME10` (10% off) and `SAVE20` (20% off)
- Spend $40 or more to get free delivery
- Place an order, return to the main menu, and open **Track orders** a bit later to see the status change

## Project structure

```
food-delivery-simulator/
├── food_delivery_simulator.py
├── README.md
└── .gitignore
```

## Ideas for extending it

- Save and load order history as JSON
- Add restaurants, each with their own menu
- Add unit tests for `Cart.totals()` with pytest
- Add a driver rating step after delivery

## Author

Chibuike Daniel Chukwuma
