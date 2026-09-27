"""FIN-MATE 數值計算工具：安全地計算浮點算術表達式。

一個 `calc` 純 function，允許 + - * / ** ( ) 與小數，其餘一律拒絕
（AST 白名單），避免任意程式碼執行。
"""
from __future__ import annotations

import ast
import operator
from typing import Any

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow):
            return float(left ** right)
        return float(_BIN_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return float(_UNARY_OPS[type(node.op)](_eval_node(node.operand)))
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def calc(expr: str) -> dict[str, Any]:
    """計算一個安全嘅數值算術表達式。

    支援常數與 +、-、*、/、**、括號。唔支援變數、函式、字串或其餘
    Python 語法（AST 白名單）。

    Args:
        expr: 算術表達式字串，例："100 * (1 + 0.05) ** 3"。

    Returns:
        {"expr": ..., "result": ...}；失敗時 result 為 None 並附 error。
    """
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval_node(tree)
        return {"expr": expr, "result": result}
    except Exception as exc:  # noqa: BLE001 - 統一回傳錯誤，唔抛畀模型
        return {"expr": expr, "result": None, "error": str(exc)}
