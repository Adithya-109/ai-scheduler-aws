def is_p(n):
    if n<2: return False
    i=2
    while i*i<=n:
        if n%i==0: return False
        i+=1
    return True
print(sum(1 for k in range(200000) if is_p(k)))
