import random
random.seed(1)
x=[random.random() for _ in range(1_200_000)]
x.sort()
print(x[0])
