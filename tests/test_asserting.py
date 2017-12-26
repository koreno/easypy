import pytest

from easypy.asserting import ASSERT


def test_assert_ok():
    x = 1
    y = 2
    z = 3

    ASSERT('`first number:x` + `:y` `equals|==` `z`')


def test_assert_fails_proper_message():
    x = 1
    y = 2
    z = 4

    with pytest.raises(AssertionError) as exc:
        ASSERT('`first number:x` + `:y` `equals|==` `z`')

    assert str(exc.value) == 'first number(1) + y(2) equals 4'
