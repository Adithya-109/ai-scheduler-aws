import numpy as np
rng=np.random.default_rng(2)
A=rng.random((1200,1200))
print(float(np.linalg.inv(A).trace()))
