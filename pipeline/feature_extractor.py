import ast
import math

class CodeFeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        self.num_lines = 0
        self.loop_depth = 0
        self._current_depth = 0
        self.num_loops = 0
        self.num_operations = 0
        self.has_heavy_lib = 0
        self.num_function_calls = 0
        self.num_comprehensions = 0
        self.max_integer = 0

    def analyze(self, code_str: str) -> dict:
        self.num_lines = len([line for line in code_str.strip().split("\n") if line.strip()])
        try:
            tree = ast.parse(code_str)
            self.visit(tree)
        except SyntaxError as e:
            return {"error": f"Syntax Error: {e}"}

        # Calculate raw complexity
        raw_complexity = 1.0
        
        if self.num_loops > 0:
            # If loops exist, the max integer acts as a multiplier based on nesting depth
            # e.g., 500 nested 3 times (depth 3) = 500^3
            raw_complexity = float(self.max_integer ** self.loop_depth)
        else:
            # No loops? Don't let a random large integer (like a phone number) trick the AI
            raw_complexity = float(self.num_lines * 10)
            
        if self.has_heavy_lib == 1:
            # Matrix operations scale polynomially. 
            raw_complexity = float(self.max_integer ** 2.5) / 10.0

        # Prevent math overflow on astronomical nested loops
        raw_complexity = min(raw_complexity, 1e12)
        raw_complexity = max(raw_complexity, 1.0) 

        # Compress the feature using Log10 to prevent Target Skew
        compressed_complexity = math.log10(raw_complexity)

        return {
            "num_lines": self.num_lines,
            "max_loop_depth": self.loop_depth,
            "num_loops": self.num_loops,
            "num_operations": self.num_operations,
            "has_heavy_lib": self.has_heavy_lib,
            "num_function_calls": self.num_function_calls,
            "num_comprehensions": self.num_comprehensions,
            "max_integer": self.max_integer,
            "estimated_complexity": compressed_complexity
        }

    def visit_For(self, node):
        self.num_loops += 1
        self._current_depth += 1
        if self._current_depth > self.loop_depth:
            self.loop_depth = self._current_depth
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_While(self, node):
        self.num_loops += 1
        self._current_depth += 1
        if self._current_depth > self.loop_depth:
            self.loop_depth = self._current_depth
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_BinOp(self, node):
        self.num_operations += 1
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in ['numpy', 'pandas', 'torch', 'tensorflow', 'scipy']:
                self.has_heavy_lib = 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in ['numpy', 'pandas', 'torch', 'tensorflow', 'scipy']:
            self.has_heavy_lib = 1
        self.generic_visit(node)
        
    def visit_Call(self, node):
        self.num_function_calls += 1
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.num_comprehensions += 1
        self.generic_visit(node)
        
    def visit_GeneratorExp(self, node):
        self.num_comprehensions += 1
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            if node.value > self.max_integer:
                self.max_integer = float(node.value)
        self.generic_visit(node)