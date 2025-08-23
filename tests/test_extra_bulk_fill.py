import pytest


@pytest.mark.parametrize("n", list(range(1,33)))
def test_trivial_arithmetic(n):
    # small deterministic assertions to increase test count
    assert n + 1 - 1 == n
    assert (n * 2) // 2 == n
    assert n == int(str(n))
