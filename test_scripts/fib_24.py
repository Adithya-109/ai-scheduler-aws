#!/usr/bin/env python3
"""Recursive fibonacci(24) — exponential time complexity."""
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
result = fib(24)
print("fib(24) =", result)
