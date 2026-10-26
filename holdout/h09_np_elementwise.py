import numpy as np
x=np.arange(5_000_000,dtype=float)
print(float(np.sqrt(x*x+1.0).sum()))
