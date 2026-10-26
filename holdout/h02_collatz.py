best=0
for start in range(1,60000):
    n=start; steps=0
    while n!=1:
        n = n//2 if n%2==0 else 3*n+1
        steps+=1
    best=max(best,steps)
print(best)
