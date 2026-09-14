import os

os.makedirs("test_scripts", exist_ok=True)

heavy_1 = """import time
# Massive sequential loop
result = 0
for i in range(25000000):
    result += 1
"""

heavy_2 = """import time
# Deep nesting
result = 0
for i in range(500):
    for j in range(500):
        for k in range(120):
            result += 1
"""

heavy_3 = """import numpy as np
# Heavy Matrix Math
A = np.random.rand(2500, 2500)
B = np.random.rand(2500, 2500)
C = np.dot(A, B)
"""

with open("test_scripts/heavy_1.py", "w") as f: f.write(heavy_1)
with open("test_scripts/heavy_2.py", "w") as f: f.write(heavy_2)
with open("test_scripts/heavy_3.py", "w") as f: f.write(heavy_3)

print("Injected 3 massive stress-test scripts into the training folder!")