#!/usr/bin/env python3
"""Write multi-second, multi-core-friendly workloads into test_scripts/.

The original set is dominated by sub-100 ms jobs, which can never justify a
network hop. These add jobs where a node with more cores should win by more
than the RTT: dense linear algebra and FFT (BLAS/LAPACK use all allowed
cores), large element-wise NumPy, plus pure-Python loops as a single-threaded
control (more cores should NOT help them). Deterministic: re-running rewrites
identical files.

    python3 generate_heavy_scripts.py
    MODE=docker ONLY='[bfec][lfwp]*_*' ./scripts/run_asymmetric_experiment.sh   # then measure them
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_scripts")

HEAD = '#!/usr/bin/env python3\n"""{doc}"""\nimport numpy as np\nrng = np.random.default_rng(0)\n'
KINDS = {
    "blasmm": ("Dense matmul {n}x{n}", [1000, 1500, 2000, 2500, 3000, 3500, 4000],
               "A = rng.random(({n}, {n}))\nB = rng.random(({n}, {n}))\nC = A @ B\nprint('matmul', float(C.sum()))\n"),
    "blassolve": ("Linear solve {n}x{n}", [1500, 2000, 2500, 3000, 3500, 4000],
                  "A = rng.random(({n}, {n})) + {n} * np.eye({n})\nb = rng.random({n})\nx = np.linalg.solve(A, b)\nprint('solve', float(x.sum()))\n"),
    "blasinv": ("Matrix inverse {n}x{n}", [800, 1200, 1600, 2000, 2400, 2800],
                "A = rng.random(({n}, {n})) + {n} * np.eye({n})\nI = np.linalg.inv(A)\nprint('inv', float(np.trace(I)))\n"),
    "blaseigh": ("Symmetric eigendecomposition {n}x{n}", [400, 600, 800, 1000, 1300],
                 "A = rng.random(({n}, {n}))\nS = A + A.T\nw = np.linalg.eigvalsh(S)\nprint('eigh', float(w.sum()))\n"),
    "blassvd": ("Singular values {n}x{n}", [400, 600, 800, 1000, 1200],
                "A = rng.random(({n}, {n}))\ns = np.linalg.svd(A, compute_uv=False)\nprint('svd', float(s.sum()))\n"),
    "fftbig": ("FFT of 2**{n} points, repeated", [18, 20, 21, 22, 23],
               "x = rng.random(2 ** {n})\nt = 0.0\nfor _ in range(4):\n    t += float(np.abs(np.fft.rfft(x)).sum())\nprint('fft', t)\n"),
    "ewisebig": ("Element-wise chain over {n} floats", [5_000_000, 10_000_000, 20_000_000, 30_000_000],
                 "x = rng.random({n})\ny = np.sqrt(x * x + 1.0) * np.exp(-x) + np.sin(x)\nprint('ewise', float(y.sum()))\n"),
    "cpuloop": ("Single-threaded pure-Python loop, {n} iterations (control)", [3_000_000, 6_000_000, 12_000_000, 20_000_000],
                "total = 0\nfor i in range({n}):\n    total += (i * i) % 7\nprint('loop', total)\n"),
}


def build() -> dict[str, str]:
    files = {}
    for kind, (doc, sizes, body) in KINDS.items():
        for n in sizes:
            uses_np = kind != "cpuloop"
            head = HEAD if uses_np else '#!/usr/bin/env python3\n"""{doc}"""\n'
            files[f"{kind}_{n}.py"] = head.format(doc=doc.format(n=n)) + body.format(n=n)
    return files


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    files = build()
    for name, code in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(code)
    print(f"wrote {len(files)} scripts to {OUT}")


if __name__ == "__main__":
    main()
