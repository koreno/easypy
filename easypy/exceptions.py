from __future__ import absolute_import

import sys
from traceback import format_exc, extract_tb
from time import time
from datetime import datetime
from contextlib import contextmanager
from textwrap import indent
from logging import getLogger


_logger = getLogger(__name__)


class PException(Exception):
    """
    An exception object that can accept kwargs as attributes

    Example::

        >>> class NotEnoughCookies(PException):
        ...     template = "You don't have enough cookies available"
        >>>
        >>> raise NotEnoughCookies(wanted=10, available=8, day='Thursday')
        Traceback (most recent call last):
            ...
        NotEnoughCookies: You don't have enough cookies available
            available = 8
            day = Thursday
            wanted = 10
    """

    def __init__(self, message="", *args, **params):
        if args or params:
            message = message.format(*args, **params)
        Exception.__init__(self, message)
        self.context = params.pop("context", None)
        self.traceback = params.pop("traceback", None)
        if self.traceback is True:
            self.traceback = format_exc()
        self.message = message
        self.timestamp = params.pop('timestamp', time())
        if 'tip' not in params:
            # sometimes it's on the class
            params['tip'] = getattr(self, 'tip', None)
        self._params = {}
        self.add_params(**params)

    def add_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        self._params.update(params)

    def __repr__(self):
        if self._params:
            kw = sorted("%s=%r" % (k, v) for k, v in self._params.items())
            return "%s(%r, %s)" % (self.__class__.__name__, self.message, ", ".join(kw))
        else:
            return "%s(%r)" % (self.__class__.__name__, self.message)

    def __str__(self):
        return self.render(traceback=False, color=False)

    def render(self, params=True, context=True, traceback=True, timestamp=True, color=True):
        text = ""

        if self.message:
            text += "".join("WHITE<<%s>>\n" % line for line in self.message.splitlines())

        if params and self._params:
            tip = self._params.pop('tip', None)
            text += indent("".join(make_block(self._params)), " " * 4)
            if tip:
                tip = tip.format(**self._params)
                lines = tip.splitlines()
                text += indent("GREEN(BLUE)@{tip = %s}@\n" % lines[0], " " * 4)
                for line in lines[1:]:
                    text += indent("GREEN(BLUE)@{      %s}@\n" % lines[0], " " * 4)
                self._params['tip'] = tip  # put it back in params, even though it might've been on the class

        if timestamp and self.timestamp:
            ts = datetime.fromtimestamp(self.timestamp).isoformat()
            text += indent("MAGENTA<<timestamp = %s>>\n" % ts, " " * 4)

        if context and self.context:
            text += "Context:\n" + indent("".join(make_block(self.context, skip={"indentation"})), " " * 4)

        if traceback and self.traceback:
            fmt = "DARK_GRAY@{{{}}}@"
            text += "\n".join(map(fmt.format, self.traceback.splitlines()))

        if not color:
            from easypy.colors import colorize_by_patterns
            text = colorize_by_patterns(text, no_color=True)

        return text

    @classmethod
    def make(cls, name):
        return type(name, (cls,), {})

    @classmethod
    @contextmanager
    def on_exception(cls, acceptable=Exception, **kwargs):
        try:
            yield
        except cls:
            # don't mess with exceptions of this type
            raise
        except acceptable as exc:
            exc_info = sys.exc_info()
            _logger.debug("'%s' raised; Raising as '%s'" % (type(exc), cls), exc_info=exc_info)
            raise cls(traceback=True, **kwargs) from None


class TException(PException):
    """ An exception object with a formatted message

    Makes it easier to reuse an exception message template.
    This object must be defined with a *template* property, this template will
    be formatted with later passed keyword arguments. You may pass kwargs which
    are not included in the template string.

    Example::

        >>> class NotEnoughPeanuts(TException):
        ...     template = "You can't have {wanted} peanuts, there are only {available} left"
        >>>
        >>> raise NotEnoughPeanuts(wanted=10, available=8, day='Thursday')
        NotEnoughPeanuts: You can't have 10 peanuts, there are only 8 left
            available = 8
            day = Thursday
            wanted = 10

    """

    @property
    def template(self):
        raise NotImplementedError("Must implement template")

    def __init__(self, *args, **params):
        super(TException, self).__init__(self.template, *args, **params)

    @classmethod
    def make(cls, name, template):
        return type(name, (cls,), dict(template=template))


def make_block(d, skip={}):
    for k in sorted(d):
        if k.startswith("_"):
            continue
        if k in skip:
            continue
        v = d[k]
        if isinstance(v, datetime):
            v = v.isoformat()
        elif not isinstance(v, str):
            v = repr(v)
        dark = False
        if k.startswith("~"):
            k = k[1:]
            dark = True
        head = "%s = " % k
        block = indent(v, " " * len(head))
        block = head + block[len(head):]
        if dark:
            block = "DARK_GRAY@{%s}@" % block
        yield block + "\n"


def convert_traceback_to_list(tb):
    """
    Convert a traceback to to list of dictionaries that contain file, line_no and function

    :param tb: A traceback object
    :type tb: ``builtins.traceback``
    """

    return [
        dict(file=file, line_no=line_no, function=function)
        for file, line_no, function, _ in extract_tb(tb)
    ]
