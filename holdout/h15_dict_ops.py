d={}
for i in range(1_000_000):
    d[i%5000]=d.get(i%5000,0)+i
print(len(d))
