#!/usr/bin/env python3
"""
Generate diverse test scripts that span the 0.1s–10s execution range
with varied computational profiles. This fills the gap in the original
dataset where 75% of scripts were < 50ms and there was almost nothing
in the 0.1–2s range.
"""
import os

SCRIPT_DIR = "test_scripts"

# Each template is (filename_prefix, code_template, param_list)
# param_list is a list of dicts that get .format()'d into the template
TEMPLATES = []

# === Category 1: Pure Python Loops (varying iteration counts) ===
loop_template = '''#!/usr/bin/env python3
"""Heavy pure-Python loop: {n} iterations."""
result = 0
for i in range({n}):
    result += i * 3 + 7
print("Loop result:", result)
'''
for n in [50000, 100000, 250000, 500000, 1000000, 2000000, 5000000, 
          7500000, 10000000, 15000000, 20000000]:
    TEMPLATES.append((f"loop_{n}", loop_template, {"n": n}))

# === Category 2: Nested Loops ===
nested_template = '''#!/usr/bin/env python3
"""Nested loop: {outer}x{inner} iterations."""
result = 0
for i in range({outer}):
    for j in range({inner}):
        result += i ^ j
print("Nested result:", result)
'''
for outer, inner in [(100, 5000), (200, 5000), (500, 2000), (1000, 1000),
                     (500, 5000), (1000, 5000), (2000, 3000), (100, 50000),
                     (50, 100000), (500, 10000)]:
    TEMPLATES.append((f"nested_{outer}x{inner}", nested_template, {"outer": outer, "inner": inner}))

# === Category 3: Triple-Nested Loops ===
triple_template = '''#!/usr/bin/env python3
"""Triple nested loop: {a}x{b}x{c}."""
result = 0
for i in range({a}):
    for j in range({b}):
        for k in range({c}):
            result += 1
print("Triple nested:", result)
'''
for a, b, c in [(50, 50, 200), (100, 100, 50), (80, 80, 80), 
                (200, 100, 30), (50, 50, 500), (100, 100, 100),
                (150, 100, 50), (200, 200, 20)]:
    TEMPLATES.append((f"triple_{a}x{b}x{c}", triple_template, {"a": a, "b": b, "c": c}))

# === Category 4: Numpy Matrix Operations ===
numpy_template = '''#!/usr/bin/env python3
"""Numpy matrix multiplication: {size}x{size}."""
import numpy as np
size = {size}
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Matrix shape:", C.shape, "sum:", C.sum())
'''
for size in [200, 400, 600, 800, 1000, 1200, 1500, 1800, 2000, 2500, 3000]:
    TEMPLATES.append((f"numpy_matmul_{size}", numpy_template, {"size": size}))

# === Category 5: Numpy Array Operations (non-matmul) ===
numpy_ops_template = '''#!/usr/bin/env python3
"""Numpy array operations on {n} elements."""
import numpy as np
arr = np.random.rand({n})
result = np.sort(arr)
result = np.fft.fft(result[:min(len(result), 100000)])
print("Array ops done, shape:", result.shape)
'''
for n in [100000, 500000, 1000000, 2000000, 5000000, 10000000]:
    TEMPLATES.append((f"numpy_ops_{n}", numpy_ops_template, {"n": n}))

# === Category 6: List Sorting ===
sort_template = '''#!/usr/bin/env python3
"""Sort a list of {n} random integers."""
import random
random.seed(42)
data = [random.randint(0, 10**9) for _ in range({n})]
data.sort()
print("Sorted", len(data), "elements, first:", data[0], "last:", data[-1])
'''
for n in [100000, 250000, 500000, 750000, 1000000, 2000000]:
    TEMPLATES.append((f"sort_{n}", sort_template, {"n": n}))

# === Category 7: String Operations ===
string_template = '''#!/usr/bin/env python3
"""Heavy string concatenation and processing: {n} iterations."""
parts = []
for i in range({n}):
    parts.append(str(i) * 3)
big_string = ",".join(parts)
count = big_string.count("1")
print("String length:", len(big_string), "count of 1:", count)
'''
for n in [50000, 100000, 250000, 500000, 1000000]:
    TEMPLATES.append((f"string_{n}", string_template, {"n": n}))

# === Category 8: Recursive Fibonacci (intentionally slow) ===
fib_template = '''#!/usr/bin/env python3
"""Recursive fibonacci({n}) — exponential time complexity."""
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
result = fib({n})
print("fib({n}) =", result)
'''
for n in [20, 24, 27, 29, 31, 33, 35]:
    TEMPLATES.append((f"fib_{n}", fib_template, {"n": n}))

# === Category 9: Dictionary Operations ===
dict_template = '''#!/usr/bin/env python3
"""Dictionary insert + lookup: {n} operations."""
data = {{}}
for i in range({n}):
    data[f"key_{{i}}_{{i**2}}"] = i * 7 + 3
lookups = 0
for i in range({n}):
    if f"key_{{i}}_{{i**2}}" in data:
        lookups += 1
print("Dict size:", len(data), "lookups:", lookups)
'''
for n in [100000, 250000, 500000, 1000000, 2000000]:
    TEMPLATES.append((f"dict_{n}", dict_template, {"n": n}))

# === Category 10: Comprehension-Heavy ===
comp_template = '''#!/usr/bin/env python3
"""List comprehension: {n} elements with filtering."""
data = [x**2 + x for x in range({n})]
evens = [x for x in data if x % 2 == 0]
odds = [x for x in data if x % 2 == 1]
result = sum(evens) - sum(odds)
print("Comprehension result:", result, "evens:", len(evens))
'''
for n in [100000, 250000, 500000, 1000000, 2000000]:
    TEMPLATES.append((f"comp_{n}", comp_template, {"n": n}))

# === Category 11: Math-heavy (no imports) ===
math_template = '''#!/usr/bin/env python3
"""Pure math operations: {n} iterations of trig-like computation."""
result = 1.0
for i in range(1, {n}):
    result = (result * i) % 1000000007
    result += (i * i) % 997
print("Math result:", result)
'''
for n in [100000, 500000, 1000000, 2000000, 5000000, 10000000]:
    TEMPLATES.append((f"math_{n}", math_template, {"n": n}))

# === Category 12: Mixed numpy + loops ===
mixed_template = '''#!/usr/bin/env python3
"""Mixed workload: numpy + Python loop."""
import numpy as np
# Numpy part
A = np.random.rand({mat_size}, {mat_size})
B = np.linalg.inv(A + np.eye({mat_size}))
# Python loop part
total = 0
for i in range({loop_n}):
    total += i * 3
print("Mixed result:", B.sum(), total)
'''
for mat_size, loop_n in [(200, 500000), (500, 200000), (800, 100000),
                         (100, 1000000), (300, 750000), (1000, 50000),
                         (400, 400000), (600, 300000)]:
    TEMPLATES.append((f"mixed_{mat_size}m_{loop_n}l", mixed_template, 
                      {"mat_size": mat_size, "loop_n": loop_n}))


def main():
    os.makedirs(SCRIPT_DIR, exist_ok=True)
    
    count = 0
    for name, template, params in TEMPLATES:
        filepath = os.path.join(SCRIPT_DIR, f"{name}.py")
        code = template.format(**params)
        with open(filepath, 'w') as f:
            f.write(code)
        count += 1
    
    print(f"Generated {count} diverse test scripts in '{SCRIPT_DIR}/'")
    
    # Summary
    categories = {}
    for name, _, _ in TEMPLATES:
        cat = name.split("_")[0]
        categories[cat] = categories.get(cat, 0) + 1
    print("\nBreakdown by category:")
    for cat, n in sorted(categories.items()):
        print(f"  {cat:15s}: {n} scripts")


if __name__ == "__main__":
    main()
