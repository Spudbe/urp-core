"""Built-in deterministic tools for URP receipt verification.

Each function takes a dict (the receipt's input_inline) and returns a dict
(the expected output_inline). These are pure functions with no randomness,
no external state, and no side effects — suitable for ReplayClass.STRONG
verification.

Usage:

    from urp.deterministic_tools import BUILTIN_TOOLS, compute_fibonacci

    # Register all built-in tools with a verifier:
    for name, fn in BUILTIN_TOOLS.items():
        verifier.register(name, fn)
"""

from __future__ import annotations


def compute_fibonacci(inputs: dict) -> dict:
    """Pure, deterministic Fibonacci computation.

    Args:
        inputs: Dict with key "n" (int >= 0).

    Returns:
        Dict with "input", "result", and "algorithm" keys.

    Raises:
        ValueError: If n is negative.
        KeyError: If "n" is missing from inputs.
    """
    n = inputs["n"]
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"n must be a non-negative integer, got {n!r}")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return {"input": n, "result": a, "algorithm": "iterative"}


def compute_factorial(inputs: dict) -> dict:
    """Pure, deterministic factorial computation.

    Args:
        inputs: Dict with key "n" (int >= 0).

    Returns:
        Dict with "input", "result", and "algorithm" keys.

    Raises:
        ValueError: If n is negative or too large.
        KeyError: If "n" is missing from inputs.
    """
    n = inputs["n"]
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"n must be a non-negative integer, got {n!r}")
    if n > 1000:
        raise ValueError(f"n={n} is too large (max 1000)")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return {"input": n, "result": result, "algorithm": "iterative"}


def compute_sha256(inputs: dict) -> dict:
    """Compute SHA-256 hash of a string.

    Args:
        inputs: Dict with key "data" (str).

    Returns:
        Dict with "input", "hash", and "algorithm" keys.

    Raises:
        KeyError: If "data" is missing from inputs.
    """
    import hashlib
    data = inputs["data"]
    hex_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return {"input": data, "hash": hex_digest, "algorithm": "sha256"}


def math_eval(inputs: dict) -> dict:
    """Evaluate a simple arithmetic expression safely.

    Supports: +, -, *, /, //, %, ** and parentheses with integer/float
    operands only. No variable names, no imports, no builtins.

    Args:
        inputs: Dict with key "expression" (str).

    Returns:
        Dict with "expression", "result", and "algorithm" keys.

    Raises:
        ValueError: If the expression contains disallowed characters.
        KeyError: If "expression" is missing from inputs.
    """
    import ast
    import operator

    expr = inputs["expression"]

    # Whitelist: digits, operators, parens, whitespace, dots
    allowed = set("0123456789+-*/%() .")
    if not all(c in allowed for c in expr):
        raise ValueError(f"Expression contains disallowed characters: {expr!r}")

    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _eval_node(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval_node(node.operand))
        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    tree = ast.parse(expr, mode="eval")
    result = _eval_node(tree)

    # Normalise int results
    if isinstance(result, float) and result == int(result):
        result = int(result)

    return {"expression": expr, "result": result, "algorithm": "ast_eval"}


# Registry of all built-in deterministic tools.
# Keys are tool_name values that match ToolReceipt.tool_name.
BUILTIN_TOOLS: dict[str, callable] = {
    "compute_fibonacci": compute_fibonacci,
    "compute_factorial": compute_factorial,
    "compute_sha256": compute_sha256,
    "math_eval": math_eval,
}
