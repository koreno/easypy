import easypy
import pkgutil
import pytest
import sys

packages = [name for ff, name, is_pkg in pkgutil.walk_packages(easypy.__path__)]


@pytest.mark.parametrize("package", packages)
def test_package(package):
    for n in sorted(sys.modules):
        if n.startswith("easypy."):
            sys.modules.pop(n)
    __import__("easypy.%s" % package)
