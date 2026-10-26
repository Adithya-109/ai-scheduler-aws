"""Static (never-executing) cost estimation for Python source.

The extractor walks the AST once and estimates how much work the program does,
in log10 "equivalent Python bytecode operations". Everything is computed in log
space, so astronomically large loop nests cannot overflow.

What it models (and what the old extractor did not):

* each loop's trip count comes from *its own* ``range()`` bound (constants and
  simple variables are resolved), multiplied down the nesting path; sequential
  loops add, they don't take a global max;
* list/dict/set comprehensions are loops over their iterables;
* user functions are costed at their call sites; self-recursion is detected and
  costed from the call argument (``fib(35)`` vs ``fib(20)``), with memoised
  functions treated as linear;
* NumPy work is tracked separately: array sizes flow through simple
  assignments, ``dot``/``matmul``/``linalg`` are costed as flops, sort/FFT as
  n log n, everything else as element-wise;
* time-bounded busy-waits (``while perf_counter() - t0 < 2.0``) and ``sleep``
  are read as wall-clock seconds.

Known limits: no inter-procedural data flow beyond constant arguments, no
class hierarchies, unknown loop bounds default to 100 iterations (1000 for
``while``), and anything it cannot resolve falls back to those defaults rather
than guessing high. Features describe *work*, not hardware: the speed of the
edge vs cloud machine is the regressors' job.
"""
from __future__ import annotations

import ast
import math

FEATURE_VERSION = 2
FEATURE_COLUMNS = [
    "num_lines", "num_loops", "max_loop_depth", "num_operations",
    "has_heavy_lib", "num_function_calls", "num_comprehensions",
    "has_recursion", "time_bound_s",
    "log_python_ops", "log_numpy_elems", "log_blas_flops",
    "estimated_complexity",
]

HEAVY_LIBS = {"numpy", "pandas", "torch", "tensorflow", "scipy", "sklearn", "jax", "numba", "cupy"}

# Rough hardware ratios used only to fold the three work counters into one
# "equivalent Python ops" number. The regressors see all three separately.
ELEMENT_OFFSET = 1.5   # a vectorised NumPy element op ~30x cheaper than a bytecode op
FLOP_OFFSET = 3.0      # BLAS flops ~1000x cheaper than bytecode ops
C_BUILTIN_OFFSET = 1.0  # sorted()/sum() inner loops ~10x cheaper than bytecode ops
PY_OPS_PER_SEC = 1e7   # converts a wall-clock bound into an op count
DEFAULT_TRIPS_LOG = 2.0        # unknown for-loop bound: 100 iterations
DEFAULT_WHILE_TRIPS_LOG = 3.0  # unknown while-loop bound: 1000 iterations
DEFAULT_ARRAY_ELEMS = 1e4
MAX_LOG = 12.0
NODE_BUDGET = 200_000

NEG = float("-inf")


def _lse(a: float, b: float) -> float:
    """log10(10**a + 10**b), safe for -inf."""
    if a == NEG:
        return b
    if b == NEG:
        return a
    if a < b:
        a, b = b, a
    return a + math.log10(1.0 + 10.0 ** (b - a))


class Cost:
    """Work in log10 units, split by kind. -inf means zero."""
    __slots__ = ("py", "elems", "flops")

    def __init__(self, py: float = NEG, elems: float = NEG, flops: float = NEG):
        self.py, self.elems, self.flops = py, elems, flops

    def __add__(self, o: "Cost") -> "Cost":
        return Cost(_lse(self.py, o.py), _lse(self.elems, o.elems), _lse(self.flops, o.flops))

    def scaled(self, log_n: float) -> "Cost":
        return Cost(self.py + log_n, self.elems + log_n, self.flops + log_n)

    def vmax(self, o: "Cost") -> "Cost":
        return Cost(max(self.py, o.py), max(self.elems, o.elems), max(self.flops, o.flops))

    def total_log(self) -> float:
        return _lse(_lse(self.py, self.elems - ELEMENT_OFFSET), self.flops - FLOP_OFFSET)


ONE = Cost(py=0.0)
ZERO = Cost()


class _Budget(Exception):
    pass


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _log10(x: float) -> float:
    return math.log10(max(x, 1.0))


def _prod(dims) -> float:
    p = 1.0
    for d in dims:
        p *= max(d, 1.0)
    return p


_NP_CREATORS_DIMS = {"rand", "randn", "zeros", "ones", "empty", "eye", "identity", "random_sample", "random", "full",
                     "standard_normal", "standard_exponential"}
_NP_GENERATOR_CTORS = {"default_rng", "RandomState", "Generator"}
_NP_BLAS = {"dot", "matmul", "inner", "tensordot", "einsum", "inv", "solve", "svd", "eig", "eigh",
            "det", "qr", "cholesky", "lstsq", "pinv", "matrix_power", "eigvalsh", "eigvals", "svdvals", "slogdet"}
_NP_NLOGN = {"sort", "argsort", "fft", "ifft", "fft2", "ifft2", "rfft", "unique", "searchsorted",
             "partition", "lexsort"}
_NP_UNARY_KEEP_SHAPE = _NP_NLOGN | {"abs", "exp", "log", "sqrt", "sin", "cos", "tanh", "cumsum", "cumprod",
                                    "transpose", "copy", "clip", "square", "inv", "pinv", "diff", "flip"}
_LINEAR_BUILTINS = {"sum", "min", "max", "list", "tuple", "set", "sorted", "reversed", "any", "all",
                    "dict", "join", "count", "index", "copy", "sort", "frozenset"}
_TIME_FUNCS = {"time", "perf_counter", "monotonic", "process_time", "perf_counter_ns", "monotonic_ns", "time_ns"}
_MEMO_PARAMS = {"cache", "memo", "memoize", "memoized", "lookup", "_cache", "_memo"}
_MEMO_DECORATORS = {"lru_cache", "cache", "cached", "memoize", "cache_result"}


class _Analyzer:
    """One-shot cost walk over a parsed module. Create a new one per source."""

    def __init__(self, tree: ast.Module):
        self.tree = tree
        self.consts: dict[str, float] = {}
        self.sizes: dict[str, float] = {}      # name -> log10(len)
        self.arrays: dict[str, tuple] = {}     # name -> dims
        self.gens: set[str] = set()            # names bound to a numpy Generator / RandomState
        self.stack: list[str] = []
        self.memo: dict = {}
        self.ticks = 0
        self.time_bound_s = 0.0
        self.recursive = False
        self.funcs: dict[str, ast.FunctionDef] = {}
        self.classes: dict[str, ast.ClassDef] = {}
        self.methods: dict[str, ast.FunctionDef | None] = {}  # None = ambiguous name
        self.np_roots: set[str] = set()
        self.np_funcs: set[str] = set()
        self.max_number = 0.0
        self._index(tree)

    # ---------------------------------------------------------------- setup
    def _index(self, tree: ast.Module) -> None:
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.split(".")[0] == "numpy":
                        self.np_roots.add(a.asname or a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom):
                if n.level == 0 and (n.module or "").split(".")[0] == "numpy":
                    for a in n.names:
                        self.np_funcs.add(a.asname or a.name)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs.setdefault(n.name, n)  # type: ignore[arg-type]
            elif isinstance(n, ast.ClassDef):
                self.classes.setdefault(n.name, n)
            elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                self.max_number = max(self.max_number, abs(float(n.value)))
        for c in self.classes.values():
            for item in c.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name in self.methods:
                        self.methods[item.name] = None
                    else:
                        self.methods[item.name] = item  # type: ignore[assignment]
        # a name defined at module level wins over a method of the same name
        for name in list(self.methods):
            if name in self.funcs and self.funcs[name] is not self.methods[name]:
                self.methods[name] = None

    def _tick(self) -> None:
        self.ticks += 1
        if self.ticks > NODE_BUDGET:
            raise _Budget

    def run(self) -> Cost:
        return self._block(self.tree.body)

    # ------------------------------------------------------------ constants
    def _const(self, e: ast.AST | None) -> float | None:
        if e is None:
            return None
        if isinstance(e, ast.Constant):
            v = e.value
            return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        if isinstance(e, ast.Name):
            return self.consts.get(e.id)
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, (ast.USub, ast.UAdd)):
            v = self._const(e.operand)
            return None if v is None else (-v if isinstance(e.op, ast.USub) else v)
        if isinstance(e, ast.BinOp):
            a, b = self._const(e.left), self._const(e.right)
            if a is None or b is None:
                return None
            try:
                op = e.op
                if isinstance(op, ast.Add):
                    return a + b
                if isinstance(op, ast.Sub):
                    return a - b
                if isinstance(op, ast.Mult):
                    return a * b
                if isinstance(op, (ast.Div, ast.FloorDiv)):
                    return a / b if b else None
                if isinstance(op, ast.Mod):
                    return a % b if b else None
                if isinstance(op, ast.Pow):
                    if abs(b) > 400 or abs(a) > 1e9:
                        return None
                    return float(a ** b)
            except (OverflowError, ValueError, ZeroDivisionError):
                return None
            return None
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name):
            fn, args = e.func.id, [self._const(a) for a in e.args]
            if fn in ("int", "float", "abs") and len(args) == 1 and args[0] is not None:
                return abs(args[0]) if fn == "abs" else args[0]
            if fn in ("min", "max") and args and all(a is not None for a in args):
                return min(args) if fn == "min" else max(args)  # type: ignore[type-var]
            if fn == "len" and len(e.args) == 1 and isinstance(e.args[0], ast.Name):
                s = self.sizes.get(e.args[0].id)
                return None if s is None else 10.0 ** s
        return None

    # ------------------------------------------------------- sizes / arrays
    def _np_name(self, call: ast.Call) -> str | None:
        """Return the numpy function's last name if this call targets numpy."""
        d = _dotted(call.func)
        if d is None:
            return None
        root = d.split(".")[0]
        if root in self.np_roots:
            return d.split(".")[-1]
        if isinstance(call.func, ast.Name) and call.func.id in self.np_funcs:
            return call.func.id
        # rng = np.random.default_rng(0); rng.random((n, n)) is a numpy call too
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) \
                and call.func.value.id in self.gens:
            return call.func.attr
        return None

    def _is_generator_ctor(self, value: ast.AST | None) -> bool:
        if not isinstance(value, ast.Call):
            return False
        d = _dotted(value.func)
        if d is None or d.split(".")[-1] not in _NP_GENERATOR_CTORS:
            return False
        return d.split(".")[0] in self.np_roots or (isinstance(value.func, ast.Name) and value.func.id in self.np_funcs)

    def _creator_dims(self, call: ast.Call, last: str) -> tuple | None:
        a = call.args
        if last in _NP_CREATORS_DIMS:
            if len(a) == 1 and isinstance(a[0], ast.Tuple):
                vals = [self._const(x) for x in a[0].elts]
            else:
                vals = [self._const(x) for x in a]
            if last in ("eye", "identity") and len(vals) == 1 and vals[0] is not None:
                vals = [vals[0], vals[0]]
            if last == "full" and a:
                vals = [self._const(a[0])] if not isinstance(a[0], ast.Tuple) else [self._const(x) for x in a[0].elts]
            if vals and all(v is not None for v in vals):
                return tuple(vals)  # type: ignore[arg-type]
            return None
        if last == "arange" and a:
            hi = self._const(a[1] if len(a) > 1 else a[0])
            lo = self._const(a[0]) if len(a) > 1 else 0.0
            if hi is not None and lo is not None:
                return (max(hi - lo, 1.0),)
        if last == "linspace":
            num = self._const(call.args[2]) if len(call.args) > 2 else None
            for kw in call.keywords:
                if kw.arg == "num":
                    num = self._const(kw.value)
            return (num if num is not None else 50.0,)
        if last in ("randint", "integers", "normal", "uniform", "choice", "permutation"):
            for kw in call.keywords:
                if kw.arg == "size":
                    if isinstance(kw.value, ast.Tuple):
                        vals = [self._const(x) for x in kw.value.elts]
                        return tuple(vals) if all(v is not None for v in vals) else None  # type: ignore[arg-type]
                    v = self._const(kw.value)
                    return (v,) if v is not None else None
            if last in ("randint", "integers") and len(a) >= 3:
                v = self._const(a[2])
                return (v,) if v is not None else None
            if last == "permutation" and a:
                v = self._const(a[0])
                return (v,) if v is not None else None
        return None

    def _dims(self, e: ast.AST | None) -> tuple | None:
        if e is None:
            return None
        if isinstance(e, ast.Name):
            return self.arrays.get(e.id)
        if isinstance(e, ast.Subscript):
            return self._dims(e.value)
        if isinstance(e, ast.Attribute) and e.attr == "T":
            d = self._dims(e.value)
            return tuple(reversed(d)) if d else None
        if isinstance(e, ast.BinOp):
            ld, rd = self._dims(e.left), self._dims(e.right)
            if isinstance(e.op, ast.MatMult):
                return self._matmul_dims(ld, rd)
            cands = [d for d in (ld, rd) if d]
            return max(cands, key=_prod) if cands else None
        if isinstance(e, ast.Call):
            last = self._np_name(e)
            if last:
                d = self._creator_dims(e, last)
                if d:
                    return d
                if last in ("dot", "matmul") and len(e.args) >= 2:
                    return self._matmul_dims(self._dims(e.args[0]), self._dims(e.args[1]))
                if last in _NP_UNARY_KEEP_SHAPE and e.args:
                    return self._dims(e.args[0])
            elif isinstance(e.func, ast.Attribute) and e.func.attr == "dot" and e.args:
                return self._matmul_dims(self._dims(e.func.value), self._dims(e.args[0]))
        return None

    @staticmethod
    def _matmul_dims(a: tuple | None, b: tuple | None) -> tuple | None:
        if a and b and len(a) == 2 and len(b) == 2:
            return (a[0], b[1])
        cands = [d for d in (a, b) if d]
        return max(cands, key=_prod) if cands else None

    def _size_of(self, e: ast.AST | None) -> float | None:
        """log10 of the length of a sequence-valued expression, if knowable."""
        if e is None:
            return None
        if isinstance(e, ast.Name):
            return self.sizes.get(e.id)
        if isinstance(e, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            n = len(e.keys) if isinstance(e, ast.Dict) else len(e.elts)
            return _log10(n)
        if isinstance(e, ast.Constant) and isinstance(e.value, (str, bytes)):
            return _log10(len(e.value))
        if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return sum(self._trips(g.iter) for g in e.generators)
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mult):
            for seq, other in ((e.left, e.right), (e.right, e.left)):
                s, n = self._size_of(seq), self._const(other)
                if s is not None and n is not None and isinstance(seq, (ast.List, ast.Tuple)):
                    return s + _log10(n)
            return None
        if isinstance(e, ast.Call):
            if isinstance(e.func, ast.Name):
                if e.func.id == "range":
                    return self._range_trips(e)
                if e.func.id in ("list", "tuple", "set", "sorted", "reversed", "frozenset") and e.args:
                    return self._size_of(e.args[0])
            d = self._dims(e)
            if d:
                return _log10(_prod(d))
        d = self._dims(e)
        if d:
            return _log10(_prod(d))
        return None

    def _range_trips(self, call: ast.Call) -> float:
        v = [self._const(a) for a in call.args]
        if not v or any(x is None for x in v):
            return DEFAULT_TRIPS_LOG
        if len(v) == 1:
            start, stop, step = 0.0, v[0], 1.0
        elif len(v) == 2:
            start, stop, step = v[0], v[1], 1.0
        else:
            start, stop, step = v[0], v[1], v[2]
        if not step:
            return DEFAULT_TRIPS_LOG
        return _log10((stop - start) / step)  # type: ignore[operator]

    def _trips(self, it: ast.AST) -> float:
        """log10 of the iteration count of a for-loop / comprehension source."""
        if isinstance(it, ast.Call):
            if isinstance(it.func, ast.Name):
                fn = it.func.id
                if fn == "range":
                    return min(self._range_trips(it), 9.0)
                if fn in ("enumerate", "reversed", "sorted", "list", "tuple", "set", "iter", "zip", "frozenset") and it.args:
                    return self._trips(it.args[0])
            if isinstance(it.func, ast.Attribute) and it.func.attr in ("items", "values", "keys"):
                s = self._size_of(it.func.value)
                return DEFAULT_TRIPS_LOG if s is None else s
        s = self._size_of(it)
        return min(DEFAULT_TRIPS_LOG if s is None else s, 9.0)

    # ------------------------------------------------------------ statements
    def _block(self, stmts) -> Cost:
        total = Cost()
        for s in stmts:
            total = total + self._stmt(s)
        return total

    def _bind(self, target: ast.AST, value: ast.AST | None) -> None:
        if not isinstance(target, ast.Name):
            return
        name = target.id
        if self._is_generator_ctor(value):
            self.gens.add(name)
        else:
            self.gens.discard(name)
        for table, getter in ((self.consts, self._const), (self.sizes, self._size_of)):
            v = getter(value)
            if v is None:
                table.pop(name, None)
            else:
                table[name] = v
        d = self._dims(value)
        if d:
            self.arrays[name] = d
        else:
            self.arrays.pop(name, None)

    def _unbind(self, target: ast.AST) -> None:
        for n in ast.walk(target):
            if isinstance(n, ast.Name):
                self.consts.pop(n.id, None)
                self.sizes.pop(n.id, None)
                self.arrays.pop(n.id, None)

    def _stmt(self, node: ast.stmt) -> Cost:
        self._tick()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return ZERO
        if isinstance(node, ast.Assign):
            cost = ONE + self._expr(node.value)
            for t in node.targets:
                self._bind(t, node.value)
            return cost
        if isinstance(node, ast.AnnAssign):
            cost = ONE + (self._expr(node.value) if node.value else ZERO)
            if node.value is not None:
                self._bind(node.target, node.value)
            return cost
        if isinstance(node, ast.AugAssign):
            cost = ONE + self._expr(node.value)
            self._unbind(node.target)
            return cost
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return self._for(node)
        if isinstance(node, ast.While):
            return self._while(node)
        if isinstance(node, ast.If):
            c = self._expr(node.test)
            a = self._block(node.body)
            b = self._block(node.orelse)
            return ONE + c + a.vmax(b)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            c = Cost()
            for item in node.items:
                c = c + self._expr(item.context_expr)
            return c + self._block(node.body)
        if isinstance(node, ast.Try) or node.__class__.__name__ == "TryStar":
            c = self._block(node.body) + self._block(node.orelse) + self._block(node.finalbody)  # type: ignore[attr-defined]
            h = Cost()
            for handler in node.handlers:  # type: ignore[attr-defined]
                h = h.vmax(self._block(handler.body))
            return c + h
        if isinstance(node, ast.Expr):
            return ONE + self._expr(node.value)
        if isinstance(node, (ast.Return, ast.Assert, ast.Raise, ast.Delete)):
            c = ONE
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    c = c + self._expr(child)
            return c
        c = Cost()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                c = c + self._stmt(child)
            elif isinstance(child, ast.expr):
                c = c + self._expr(child)
        return c

    def _for(self, node) -> Cost:
        trips = self._trips(node.iter)
        head = self._expr(node.iter)
        it = node.iter
        self._unbind(node.target)
        if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"
                and isinstance(node.target, ast.Name)):
            v = [self._const(a) for a in it.args]
            if v and all(x is not None for x in v):
                lo, hi = (0.0, v[0]) if len(v) == 1 else (v[0], v[1])
                self.consts[node.target.id] = (lo + hi) / 2.0  # type: ignore[operator]
        body = self._block(node.body) + ONE
        if getattr(node, "orelse", None):
            body = body + self._block(node.orelse).scaled(-trips)
        return head + body.scaled(trips)

    def _time_bound(self, test: ast.AST) -> float | None:
        calls = [n for n in ast.walk(test) if isinstance(n, ast.Call)]
        timey = [c for c in calls if (_dotted(c.func) or "").split(".")[-1] in _TIME_FUNCS]
        if not timey:
            return None
        nums = [n.value for n in ast.walk(test)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
        if not nums:
            return None
        secs = float(max(nums))
        if any((_dotted(c.func) or "").endswith("_ns") for c in timey):
            secs /= 1e9
        return secs

    def _while(self, node: ast.While) -> Cost:
        secs = self._time_bound(node.test)
        if secs is not None:
            self.time_bound_s = max(self.time_bound_s, secs)
            return Cost(py=_log10(secs * PY_OPS_PER_SEC)) + self._block(node.body)
        trips = DEFAULT_WHILE_TRIPS_LOG
        t = node.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1:
            left, right = self._const(t.left), self._const(t.comparators[0])
            bound = right if right is not None else left
            if bound is not None and bound > 0 and (left is None or right is None):
                trips = min(_log10(bound), 9.0)
        head = self._expr(node.test)
        body = self._block(node.body) + ONE
        return head + body.scaled(trips)

    # ------------------------------------------------------------ expressions
    def _expr(self, node: ast.AST | None) -> Cost:
        if node is None:
            return ZERO
        self._tick()
        if isinstance(node, (ast.Constant, ast.Name, ast.Lambda)):
            return ZERO
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return self._comp(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.BinOp):
            c = self._expr(node.left) + self._expr(node.right)
            if isinstance(node.op, ast.MatMult):
                return c + self._blas_cost(self._dims(node.left), self._dims(node.right))
            ld, rd = self._dims(node.left), self._dims(node.right)
            cands = [d for d in (ld, rd) if d]
            if cands:
                return c + Cost(elems=_log10(_prod(max(cands, key=_prod))))
            return c + ONE
        c = ONE if isinstance(node, (ast.Compare, ast.BoolOp, ast.UnaryOp, ast.Subscript)) else ZERO
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                c = c + self._expr(child)
        return c

    def _comp(self, node) -> Cost:
        trips = 0.0
        head = Cost()
        for g in node.generators:
            trips += self._trips(g.iter)
            head = head + self._expr(g.iter)
            self._unbind(g.target)
        if isinstance(node, ast.DictComp):
            elt = self._expr(node.key) + self._expr(node.value)
        else:
            elt = self._expr(node.elt)
        return head + (ONE + elt).scaled(trips)

    def _blas_cost(self, a: tuple | None, b: tuple | None, kind: str = "matmul") -> Cost:
        if a and b and len(a) == 2 and len(b) == 2:
            flops = a[0] * a[1] * b[1]
        else:
            cands = [d for d in (a, b) if d]
            n = max(_prod(d) for d in cands) if cands else DEFAULT_ARRAY_ELEMS
            flops = n ** 1.5  # ~ n^3 for a square matrix with n^2 elements
        return Cost(flops=_log10(flops))

    def _numpy_cost(self, call: ast.Call, last: str) -> Cost:
        arrs = [self._dims(a) for a in call.args]
        created = self._creator_dims(call, last)
        if created:
            return Cost(elems=_log10(_prod(created)))
        known = [d for d in arrs if d]
        if last in _NP_BLAS:
            if last in ("dot", "matmul", "inner", "tensordot") and len(arrs) >= 2:
                return self._blas_cost(arrs[0], arrs[1])
            return self._blas_cost(known[0] if known else None, known[0] if known else None)
        n = _prod(max(known, key=_prod)) if known else (
            max((_prod(d) for d in self.arrays.values()), default=DEFAULT_ARRAY_ELEMS))
        if last in _NP_NLOGN:
            return Cost(elems=_log10(n * max(1.0, math.log2(max(n, 2.0)))))
        return Cost(elems=_log10(n))

    def _call(self, node: ast.Call) -> Cost:
        func = node.func
        args = Cost()
        for a in node.args:
            args = args + self._expr(a)
        for kw in node.keywords:
            args = args + self._expr(kw.value)
        if isinstance(func, ast.Attribute) and isinstance(func.value, (ast.Call, ast.BinOp, ast.Subscript)):
            args = args + self._expr(func.value)

        dotted = _dotted(func) or ""
        last = dotted.split(".")[-1] if dotted else (func.attr if isinstance(func, ast.Attribute) else "")

        # sleeping/time-bound: wall clock, not compute
        if dotted == "time.sleep" or (isinstance(func, ast.Name) and func.id == "sleep"):
            secs = self._const(node.args[0]) if node.args else None
            if secs:
                self.time_bound_s = max(self.time_bound_s, secs)
            return ONE + args

        np_last = self._np_name(node)
        if np_last:
            return ONE + args + self._numpy_cost(node, np_last)
        if isinstance(func, ast.Attribute) and func.attr == "dot" and node.args:
            return ONE + args + self._blas_cost(self._dims(func.value), self._dims(node.args[0]))

        if isinstance(func, ast.Name):
            if func.id in self.funcs and func.id not in self.classes:
                return ONE + args + self._call_user(self.funcs[func.id], node, skip_self=False)
            if func.id in self.classes:
                init = next((i for i in self.classes[func.id].body
                             if isinstance(i, ast.FunctionDef) and i.name == "__init__"), None)
                return ONE + args + (self._call_user(init, node, skip_self=True) if init else ZERO)
        elif isinstance(func, ast.Attribute):
            m = self.methods.get(func.attr)
            if m is not None:
                return ONE + args + self._call_user(m, node, skip_self=True)

        if last in _LINEAR_BUILTINS:
            target = node.args[0] if node.args and last not in ("sort", "join", "count", "index", "copy") else (
                func.value if isinstance(func, ast.Attribute) else None)
            if last == "join" and node.args:
                target = node.args[0]
            s = self._size_of(target)
            if s is not None and not isinstance(target, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                n = 10.0 ** s
                work = n * (max(1.0, math.log2(max(n, 2.0))) if last in ("sort", "sorted") else 1.0)
                return ONE + args + Cost(py=_log10(work) - C_BUILTIN_OFFSET)
        return ONE + args

    # -------------------------------------------------------- user functions
    def _is_memoized(self, f: ast.FunctionDef) -> bool:
        for d in f.decorator_list:
            name = _dotted(d.func if isinstance(d, ast.Call) else d) or ""
            if name.split(".")[-1] in _MEMO_DECORATORS:
                return True
        params = {a.arg for a in f.args.args + f.args.kwonlyargs}
        if params & _MEMO_PARAMS:
            return True
        return any(isinstance(n, ast.Name) and n.id in _MEMO_PARAMS for n in ast.walk(f))

    def _self_calls(self, f: ast.FunctionDef) -> list[ast.Call]:
        out = []
        for stmt in f.body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call):
                    nm = n.func.id if isinstance(n.func, ast.Name) else (
                        n.func.attr if isinstance(n.func, ast.Attribute) else None)
                    if nm == f.name:
                        out.append(n)
        return out

    def _growth(self, calls: list[ast.Call]) -> tuple[float, bool]:
        """Return (log10 branching base, halving?) for a recursive function.

        decrement style (n-1, n-2): solve sum(x**-step)=1 -> fib gives phi;
        halving style (n//2, n>>1): handled as n**log2(b).
        """
        steps, halving = [], False
        for c in calls:
            a0 = c.args[0] if c.args else None
            if isinstance(a0, ast.BinOp) and isinstance(a0.op, ast.Sub):
                k = self._const(a0.right)
                steps.append(max(k, 1.0) if k else 1.0)
            elif isinstance(a0, ast.BinOp) and isinstance(a0.op, (ast.FloorDiv, ast.Div, ast.RShift)):
                halving = True
                steps.append(1.0)
            elif isinstance(a0, ast.Subscript):  # lst[1:] / lst[:mid]
                halving = halving or isinstance(a0.slice, ast.Slice) and a0.slice.upper is not None
                steps.append(1.0)
            else:
                steps.append(1.0)
        lo, hi = 1.0, float(len(steps)) + 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if sum(mid ** -s for s in steps) > 1.0:
                lo = mid
            else:
                hi = mid
        return math.log10(max((lo + hi) / 2, 1.0)), halving

    def _call_user(self, f: ast.FunctionDef | None, call: ast.Call, skip_self: bool) -> Cost:
        if f is None:
            return ZERO
        params = [a.arg for a in f.args.args]
        if skip_self and params and params[0] in ("self", "cls"):
            params = params[1:]
        argvals = [self._const(a) for a in call.args]
        key = (f.name, tuple(argvals))
        if key in self.memo:
            return self.memo[key]
        if f.name in self.stack:
            return ZERO
        saved = (self.consts, self.sizes, self.arrays)
        self.consts, self.sizes, self.arrays = dict(self.consts), dict(self.sizes), dict(self.arrays)
        for p, a, v in zip(params, call.args, argvals):
            if v is not None:
                self.consts[p] = v
            else:
                self.consts.pop(p, None)
            s, d = self._size_of(a), self._dims(a)
            if s is not None:
                self.sizes[p] = s
            if d:
                self.arrays[p] = d
        self.stack.append(f.name)
        try:
            body = self._block(f.body)
        finally:
            self.stack.pop()
            self.consts, self.sizes, self.arrays = saved
        rec = self._self_calls(f)
        if rec:
            self.recursive = True
            n = argvals[0] if argvals and argvals[0] is not None else 20.0
            n = max(min(n, 5000.0), 1.0)
            base, halving = self._growth(rec)
            if self._is_memoized(f) or len(rec) == 1 and not halving:
                body = body.scaled(_log10(n))
            elif halving:
                body = body.scaled(_log10(n) * math.log2(max(len(rec), 1)) if len(rec) > 1 else _log10(math.log2(n + 1.0)))
            else:
                body = body.scaled(min(n, 200.0) * base)
        self.memo[key] = body
        return body


class CodeFeatureExtractor:
    """Public API: ``analyze(code) -> dict`` (or ``{"error": ...}``)."""

    def analyze(self, code_str: str) -> dict:
        lines = [ln for ln in code_str.strip().split("\n") if ln.strip()]
        try:
            tree = ast.parse(code_str)
        except (SyntaxError, ValueError, RecursionError, MemoryError) as e:
            return {"error": f"Syntax Error: {e}"}

        counts = self._count(tree)
        degraded = False
        an = _Analyzer(tree)
        try:
            cost = an.run()
        except (_Budget, RecursionError):
            degraded = True
            cost = Cost(py=_log10(max(len(lines), 1) * 10.0))

        def clamp(v: float) -> float:
            return 0.0 if v == NEG else float(min(max(v, 0.0), MAX_LOG))

        total = clamp(cost.total_log())
        feats = {
            "num_lines": len(lines),
            "max_loop_depth": counts["depth"],
            "num_loops": counts["loops"],
            "num_operations": counts["ops"],
            "has_heavy_lib": counts["heavy"],
            "num_function_calls": counts["calls"],
            "num_comprehensions": counts["comps"],
            "has_recursion": int(an.recursive),
            "time_bound_s": float(min(an.time_bound_s, 3600.0)),
            "log_python_ops": clamp(cost.py),
            "log_numpy_elems": clamp(cost.elems),
            "log_blas_flops": clamp(cost.flops),
            "estimated_complexity": total,
            # informational only; not a model feature
            "max_integer": float(an.max_number),
            "analysis_degraded": int(degraded),
        }
        return feats

    @staticmethod
    def _count(tree: ast.Module) -> dict:
        loops = ops = calls = comps = heavy = 0
        max_depth = 0

        def walk(node: ast.AST, depth: int) -> None:
            nonlocal loops, ops, calls, comps, heavy, max_depth
            for child in ast.iter_child_nodes(node):
                d = depth
                if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                    loops += 1
                    d = depth + 1
                    max_depth = max(max_depth, d)
                elif isinstance(child, (ast.BinOp, ast.AugAssign)):
                    ops += 1
                elif isinstance(child, ast.Call):
                    calls += 1
                elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    comps += 1
                elif isinstance(child, ast.Import):
                    if any(a.name.split(".")[0] in HEAVY_LIBS for a in child.names):
                        heavy = 1
                elif isinstance(child, ast.ImportFrom):
                    if child.level == 0 and (child.module or "").split(".")[0] in HEAVY_LIBS:
                        heavy = 1
                walk(child, d)

        try:
            walk(tree, 0)
        except RecursionError:
            pass
        return {"loops": loops, "ops": ops, "calls": calls, "comps": comps, "heavy": heavy, "depth": max_depth}
