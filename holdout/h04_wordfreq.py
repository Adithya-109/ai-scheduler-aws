import collections
words=[str(i%977)+'w' for i in range(1_500_000)]
c=collections.Counter(words)
print(c.most_common(3))
