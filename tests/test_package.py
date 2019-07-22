import pytest
import sys

packages = list(filter(None, """
_multithreading_init
aliasing
bunch
caching
collections
colors
concurrency
contexts
decorations
deprecation
exceptions
fixtures
gevent
humanize
interaction
lockstep
meta
misc
predicates
properties
random
resilience
signals
sync
tables
threadtree
timing
tokens
typed_struct
units
words
ziplog
""".split()))


@pytest.mark.parametrize("package", packages)
def test_package(package):
    for n in sorted(sys.modules):
        if n.startswith("easypy."):
            sys.modules.pop(n)
    __import__("easypy.%s" % package)
