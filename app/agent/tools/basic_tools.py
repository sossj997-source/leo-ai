import ast
import math
import operator
from datetime import datetime


# ==================================================
# GET TIME
# ==================================================

def get_time() -> str:
    """
    Returns the current local date and time.
    """

    now = datetime.now()

    return now.strftime(
        "%A, %d %B %Y, %I:%M:%S %p"
    )


# ==================================================
# CALCULATOR
# ==================================================

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate_node(node):
    """
    Safely evaluate a mathematical AST node.
    """

    if isinstance(node, ast.Constant):

        if isinstance(
            node.value,
            (int, float)
        ):
            return node.value

        raise ValueError(
            "Only numbers are allowed."
        )

    if isinstance(
        node,
        ast.UnaryOp
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:
            raise ValueError(
                "Unsupported unary operator."
            )

        return operation(
            _evaluate_node(node.operand)
        )

    if isinstance(
        node,
        ast.BinOp
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:
            raise ValueError(
                "Unsupported operator."
            )

        left = _evaluate_node(
            node.left
        )

        right = _evaluate_node(
            node.right
        )

        return operation(
            left,
            right
        )

    raise ValueError(
        "Invalid mathematical expression."
    )


def calculator(
    expression: str
):
    """
    Safely calculate a mathematical expression.

    Examples:
        25 * 4
        100 / 5
        2 ** 10
        (50 + 20) * 3
    """

    if not expression:
        raise ValueError(
            "Expression cannot be empty."
        )

    expression = expression.strip()

    if len(expression) > 200:
        raise ValueError(
            "Expression is too long."
        )

    try:

        tree = ast.parse(
            expression,
            mode="eval"
        )

        result = _evaluate_node(
            tree.body
        )

        if isinstance(
            result,
            float
        ) and result.is_integer():

            result = int(result)

        return result

    except ZeroDivisionError:

        raise ValueError(
            "Cannot divide by zero."
        )

    except Exception as e:

        if isinstance(
            e,
            ValueError
        ):
            raise

        raise ValueError(
            f"Invalid expression: {e}"
        )


# ==================================================
# BASIC MATH INFO
# ==================================================

def calculate_percentage(
    value: float,
    percentage: float
) -> float:
    """
    Calculate a percentage of a value.

    Example:
        calculate_percentage(500, 20)
        -> 100
    """

    return (
        value * percentage
    ) / 100