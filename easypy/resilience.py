from __future__ import absolute_import

from functools import partial, wraps, update_wrapper
from contextlib import contextmanager
from easypy.timing import Timer
from easypy.units import Duration
import random
import time

from .decorations import parametrizeable_decorator


import logging
from logging import getLogger
_logger = getLogger(__name__)


UNACCEPTABLE_EXCEPTIONS = (NameError, AttributeError, TypeError, KeyboardInterrupt)


class ExponentialBackoff:

    def __init__(self, initial=1, maximum=30, base=1.5, iteration=0):
        self.base = base
        self.initial = initial
        self.current = initial
        self.maximum = float(maximum)

    def get_current(self):
        return self.current

    def __call__(self):
        self.current = min(self.current * self.base, self.maximum)
        ret = min(self.get_current(), self.maximum)
        return ret

    def __repr__(self):
        return "{0.__class__.__name__}({0.base}, {0.initial}, {0.maximum} {0.current})".format(self)


class RandomExponentialBackoff(ExponentialBackoff):

    def get_current(self):
        return random.random() * self.current + self.initial


class ExpiringCounter(object):
    def __init__(self, times):
        self.times = times

    @property
    def expired(self):
        self.times -= 1
        return self.times < 0

    @property
    def remain(self):
        return self.times


def retry(times, func, args=[], kwargs={}, acceptable=Exception, sleep=1,
          max_sleep=False, log_level=logging.DEBUG, pred=None, unacceptable=()):

    if unacceptable is None:
        unacceptable = ()
    elif isinstance(unacceptable, tuple):
        unacceptable += UNACCEPTABLE_EXCEPTIONS
    else:
        unacceptable = (unacceptable,) + UNACCEPTABLE_EXCEPTIONS

    if isinstance(times, Timer):
        stopper = times  # a timer is a valid stopper
    elif isinstance(times, Duration):
        stopper = Timer(expiration=times)
    elif isinstance(times, int):
        stopper = ExpiringCounter(times)
    else:
        assert False, "'times' must be an 'int', 'Duration' or 'Timer', got %r" % times

    if max_sleep:
        sleep = RandomExponentialBackoff(sleep, max_sleep)
    if not pred:
        pred = lambda exc: True

    while True:
        try:
            return func(*args, **kwargs)
        except unacceptable as exc:
            raise
        except acceptable as exc:
            raise_if_async_exception(exc)
            if not pred(exc):
                raise
            if stopper.expired:
                raise
            _logger.log(log_level, "Exception thrown: %r", exc)
            sleep_for = 0
            if sleep:
                # support for ExponentialBackoff
                sleep_for = sleep() if callable(sleep) else sleep
            _logger.log(log_level, "Retrying... (%r remain) in %s seconds", stopper.remain, sleep_for)
            time.sleep(sleep_for)


def retrying(times, acceptable=Exception, sleep=1, max_sleep=False, log_level=logging.DEBUG, pred=None):
    def wrapper(func):
        @wraps(func)
        def impl(*args, **kwargs):
            return retry(
                times, func, args, kwargs,
                sleep=sleep, max_sleep=max_sleep,
                acceptable=acceptable, log_level=log_level,
                pred=pred)
        return impl
    return wrapper


class _Retry(Exception):
    pass
retrying.Retry = _Retry

retrying.debug = partial(retrying, log_level=logging.DEBUG)
retrying.info = partial(retrying, log_level=logging.INFO)
retrying.warning = partial(retrying, log_level=logging.WARNING)
retrying.error = partial(retrying, log_level=logging.ERROR)


@parametrizeable_decorator
def resilient(func=None, default=None, **kw):
    msg = "ignoring error in %s ({type})" % func.__qualname__

    @wraps(func)
    def inner(*args, **kwargs):
        with resilience(msg, **kw):
            return func(*args, **kwargs)
        return default  # we reach here only if an exception was caught and handled by resilience
    return inner


@contextmanager
def resilience(msg="ignoring error {type}", acceptable=Exception, unacceptable=(), log_level=logging.DEBUG, pred=None):
    if unacceptable is None:
        unacceptable = ()
    elif isinstance(unacceptable, tuple):
        unacceptable += UNACCEPTABLE_EXCEPTIONS
    else:
        unacceptable = (unacceptable,) + UNACCEPTABLE_EXCEPTIONS
    try:
        yield
    except unacceptable as exc:
        raise
    except acceptable as exc:
        if pred and not pred(exc):
            raise
        raise_if_async_exception(exc)
        _logger.log(log_level, msg.format(exc=exc, type=exc.__class__.__qualname__))
        if log_level > logging.DEBUG:
            _logger.debug("Traceback:", exc_info=True)


resilient.debug = partial(resilient, log_level=logging.DEBUG)
resilient.info = partial(resilient, log_level=logging.INFO)
resilient.warning = partial(resilient, log_level=logging.WARNING)
resilient.error = partial(resilient, log_level=logging.ERROR)

resilience.debug = partial(resilience, log_level=logging.DEBUG)
resilience.info = partial(resilience, log_level=logging.INFO)
resilience.warning = partial(resilience, log_level=logging.WARNING)
resilience.error = partial(resilience, log_level=logging.ERROR)


def raise_if_async_exception(exc):
    # This is so that exception raised from other threads don't get supressed by retry/resilience
    # see easypy.concurrency's raise_in_main_thread
    if getattr(exc, "_raised_asynchronously", False):
        _logger.info('Raising asynchronous error')
        raise exc


@parametrizeable_decorator
def exception_to_boolean(func, *, acceptable=Exception, unacceptable=()):
    """
    Decorator to create a function that returns ``False`` if the underlying
    function threw and ``True`` otherwise.

    :param acceptable: Exception type (or tuple of exception types) to convert to ``bool``.
    :param unacceptable: Exception type (or tuple of exception types) to let through.
        * The exceptions in ``easypy.resilience.UNACCEPTABLE_EXCEPTIONS`` will always be unacceptable.

    The underlying function or method can be accessed with the ``.func``
    attribute of the decorated one. Use this decorator to easily create chains
    of functions that are generally used as predicates but can - when needed -
    raise the underlying exception for more info.

    >>> @exception_to_boolean(acceptable=BadValueException)
    >>> def check_single_value(value):
    >>>     allowed_values = {1, 2, 3}
    >>>     if value not in allowed_values:
    >>>         raise BadValueException(bad_value=value, allowed=allowed_values)
    >>>
    >>>
    >>> @exception_to_boolean(acceptable=BadValueException)
    >>> def check_values(*values):
    >>>     for value in values:
    >>>         check_single_value.func(value)
    >>>
    >>> # Call regularly to use as a predicate
    >>>
    >>> check_values(1, 2, 3)
    True
    >>>
    >>> check_values(1, 2, 3, 4)
    False
    >>>
    >>> # Use .func() to get the exception
    >>>
    >>> check_values.func(1, 2, 3)
    >>>
    >>> check_values.func(1, 2, 3, 4)
    BadValueException: Value should be one of {1, 2, 3}, not 4
    """
    return _ExceptionToBooleanDescriptor(
        func=func,
        acceptable=acceptable,
        unacceptable=unacceptable)


class _ExceptionToBooleanDescriptor:
    def __init__(self, func, acceptable, unacceptable):
        self.func = func
        self._acceptable = acceptable
        self._unacceptable = unacceptable
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        try:
            self.func(*args, **kwargs)
        except self._unacceptable:
            raise
        except UNACCEPTABLE_EXCEPTIONS:
            raise
        except self._acceptable:
            return False
        else:
            return True

    def __get__(self, instance, owner=None):
        return type(self)(
            func=self.func.__get__(instance, owner),
            acceptable=self._acceptable,
            unacceptable=self._unacceptable)
