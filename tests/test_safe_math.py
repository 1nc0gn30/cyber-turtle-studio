import pytest
from cyber_turtle_studio.turtle_engine import safe_math_eval

NAMES = {"pi": 3.14159, "sin": lambda x: x, "sqrt": lambda x: x ** 0.5, "size": 10.0}


def test_basic_math():
    assert safe_math_eval("2 + 3 * 4", NAMES) == 14
    assert safe_math_eval("size / 2 - -1", NAMES) == 6.0
    assert safe_math_eval("sqrt(16)", NAMES) == 4.0
    assert safe_math_eval("2 ** 10", NAMES) == 1024


@pytest.mark.parametrize("bad", [
    "(1).__class__",
    "(1).__class__.__base__.__subclasses__()",
    "__import__('os')",
    "size.real",
    "9 ** 9 ** 99",
    "open('x')",
])
def test_escapes_rejected(bad):
    with pytest.raises((ValueError, SyntaxError)):
        safe_math_eval(bad, NAMES)
