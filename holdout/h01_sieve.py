def sieve(n):
    flags = [True]*(n+1)
    flags[0]=flags[1]=False
    for i in range(2,int(n**0.5)+1):
        if flags[i]:
            for j in range(i*i,n+1,i):
                flags[j]=False
    return sum(flags)
print(sieve(2_000_000))
