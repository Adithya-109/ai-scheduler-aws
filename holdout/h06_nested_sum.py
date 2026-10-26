t=0
for i in range(1500):
    for j in range(1500):
        t+=(i*j)%7
print(t)
