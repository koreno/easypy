import pytest

from easypy.resilience import exception_to_boolean


def test_exception_to_boolean():
    @exception_to_boolean
    def foo(exc):
        if isinstance(exc, type) and issubclass(exc, Exception):
            raise exc

    @exception_to_boolean
    def bar(exc):
        foo.func(exc)

    assert foo(None) == True
    assert foo(Exception) == False
    assert bar(None) == True
    assert bar(Exception) == False

    foo.func(None)
    bar.func(None)
    with pytest.raises(Exception):
        foo.func(Exception)
    with pytest.raises(Exception):
        bar.func(Exception)

    class FooException(Exception): pass

    with pytest.raises(FooException):
        foo.func(FooException)
    with pytest.raises(FooException):
        bar.func(FooException)


def test_exception_to_boolean_type_limitation():
    class FooException(Exception): pass
    class BarException(FooException): pass

    @exception_to_boolean(acceptable=FooException, unacceptable=BarException)
    def foo(exc):
        raise exc

    with pytest.raises(Exception):
        foo(Exception)
    assert foo(FooException) == False
    with pytest.raises(BarException):
        foo(BarException)


def test_exception_to_boolean_for_methods():
    class MyException(Exception): pass

    class Foo:
        @exception_to_boolean
        def bar(self):
            raise MyException

        @exception_to_boolean
        @classmethod
        def baz(cls):
            raise MyException

        @exception_to_boolean
        @staticmethod
        def qux():
            raise MyException

    assert Foo().bar() == False
    assert Foo().baz() == False
    assert Foo().qux() == False

    assert Foo.baz() == False
    assert Foo.qux() == False

    with pytest.raises(MyException):
        Foo().bar.func()
    with pytest.raises(MyException):
        Foo().baz.func()
    with pytest.raises(MyException):
        Foo().qux.func()

    with pytest.raises(MyException):
        Foo.baz.func()
    with pytest.raises(MyException):
        Foo.qux.func()
