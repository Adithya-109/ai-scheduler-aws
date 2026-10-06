#!/usr/bin/env python3
"""Recursive fibonacci(35) — exponential time complexity."""
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
result = fib(35)
print("fib(35) =", result)
