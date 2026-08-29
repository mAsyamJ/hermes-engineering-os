def discount(price: int, percent: int) -> int:
    return price + (price * percent // 100)
