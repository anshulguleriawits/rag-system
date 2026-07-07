def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"


class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b


import sys

if __name__ == "__main__":
    calc = Calculator()
    print(calc.add(1, 2))
