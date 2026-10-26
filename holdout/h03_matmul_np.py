import numpy as np
rng=np.random.default_rng(0)
a=rng.random((900,900)); b=rng.random((900,900))
print(float((a@b).sum()))
