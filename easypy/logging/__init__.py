# encoding: utf-8
from __future__ import absolute_import

import inspect
import logging
import random
import sys
import traceback
from contextlib import ExitStack
from functools import wraps, partial


class Graphics:

    class Graphical:
        LINE = "─"
        DOUBLE_LINE = "═"
        INDENT_SEGMENT   = "  │ "      # noqa
        INDENT_OPEN      = "  ├───┮ "  # noqa
        INDENT_CLOSE         = "  ╰╼"  # noqa
        INDENT_EXCEPTION     = "  ╘═"  # noqa

    class ASCII:
        LINE = "-"
        DOUBLE_LINE = "="
        INDENT_SEGMENT   = "..| "      # noqa
        INDENT_OPEN      = "..|---+ "  # noqa
        INDENT_CLOSE         = "  '-"  # noqa
        INDENT_EXCEPTION     = "  '="  # noqa


class G:
    """
    This class is not to be initialized.
    It is simply a namespace, container for lazily determined settings for this logging module
    """

    initialized = False

    IS_A_TTY = None
    GRAPHICAL = None
    COLORING = None
    GRPH = Graphics.ASCII
    NOTICE = None
    LEVEL_COLORS = None


from easypy.threadtree import ThreadContexts
from easypy.contexts import contextmanager
from easypy.tokens import if_auto, AUTO


def get_level_color(level):
    try:
        return G.LEVEL_COLORS[level]
    except KeyError:
        sorted_colors = sorted(G.LEVEL_COLORS.items(), reverse=True)
        for clevel, color in sorted_colors:
            if level > clevel:
                break
        G.LEVEL_COLORS[level] = color
        return color


THREAD_LOGGING_CONTEXT = ThreadContexts(counters="indentation", stacks="context")
get_current_context = THREAD_LOGGING_CONTEXT.flatten


def get_indentation():
    return THREAD_LOGGING_CONTEXT.indentation


class AbortedException(BaseException):
    """ Aborted base class

    Exceptions that inherit from this class will show as ABORTED in logger.indented
    """


class ContextableLoggerMixin(object):
    """
    A mixin class that provides easypy's logging functionality via the built-in logging's Logger objects:
        - context and indentation
        - per-thread logging supression and soloing
        - progress-bar support
        - and more...
    """

    @contextmanager
    def context(self, context=None, indent=False, progress_bar=False, **kw):
        if context:
            kw['context'] = context
        with ExitStack() as stack:
            stack.enter_context(THREAD_LOGGING_CONTEXT(kw))
            timing = kw.pop("timing", True)
            if indent:
                header = indent if isinstance(indent, str) else ("[%s]" % context)
                stack.enter_context(self.indented(header=header, timing=timing))
            if progress_bar:
                stack.enter_context(self.progress_bar())
            yield

    def suppressed(self):
        """
        Context manager - Supress all logging to the console from the calling thread
        """
        return ThreadControl.CONTEXT(silenced=True)

    def solo(self):
        """
        Context manager - Allow logging to the console from the calling thread only
        """
        return ThreadControl.solo()

    @contextmanager
    def indented(self, header=None, *args, level=AUTO, timing=True, footer=True):
        from easypy.timing import timing as timing_context

        level = if_auto(level, G.NOTICE)
        header = (header % args) if header else ""
        self.log(level, "WHITE@[%s]@" % header, extra=dict(decoration=G.graphics.INDENT_OPEN))
        with ExitStack() as stack:
            stack.enter_context(THREAD_LOGGING_CONTEXT(indentation=1))

            get_duration = lambda: ""
            if timing:
                timer = stack.enter_context(timing_context())
                get_duration = lambda: " in DARK_MAGENTA<<{:text}>>".format(timer.duration)

            def footer_log(color, title, decoration):
                if footer:
                    msg = "%s@[%s]@%s (%s)" % (color, title, get_duration(), header)
                    self.log(level, msg, extra=dict(decoration=decoration))
                else:
                    self.log(level, "", (), extra=dict(decoration=decoration))

            try:
                yield
            except (KeyboardInterrupt, AbortedException):
                footer_log("CYAN", "ABORTED", G.graphics.INDENT_EXCEPTION)
                raise
            except GeneratorExit:
                footer_log("DARK_GRAY", "DONE", G.graphics.INDENT_CLOSE)
            except:
                footer_log("RED", "FAILED", G.graphics.INDENT_EXCEPTION)
                raise
            else:
                footer_log("DARK_GRAY", "DONE", G.graphics.INDENT_CLOSE)

    def error_box(self, *exc, extra=None):
        if len(exc)==1:
            exc, = exc
            typ = type(exc)
            tb = None
        else:
            typ, exc, tb = exc
        header = "%s.%s" % (typ.__module__, typ.__name__)
        self.error("YELLOW@{%s}@ RED@{%s}@", header, G.graphics.LINE*(80-len(header)-1), extra=dict(decoration=G.RED(G.graphics.INDENT_OPEN)))
        with THREAD_LOGGING_CONTEXT(indentation=1, decoration=G.RED(G.graphics.INDENT_SEGMENT)):
            if hasattr(exc, "render") and callable(exc.render):
                exc_text = exc.render()
            elif tb:
                fmt = "DARK_GRAY@{{{}}}@"
                full_traceback = "".join(traceback.format_exception(typ, exc, tb))
                exc_text = "\n".join(map(fmt.format, full_traceback.splitlines()))
            else:
                exc_text = str(exc)
            for line in exc_text.splitlines():
                self.error(line)
            if extra:
                for line in extra.splitlines():
                    self.error(line)
            self.error("RED@{%s}@", G.DOUBLE_LINE*80, extra=dict(decoration=G.RED(G.graphics.INDENT_EXCEPTION)))

    def announced_vars(self, header='With locals:', *args, **kwargs):
        "Announces the variables declared in the context"
        import inspect
        frame = inspect.currentframe().f_back

        # `@contextmanager` annotates an internal `cm` function instead of the
        # `announced_vars` method so that `inspect.currentframe().f_back` will
        # point to the frame that uses `announced_vars`. If we decoraed
        # `announced_vars` with `@contextmanager`, we'd have to depend on
        # implementation details of `@contextmanager` - currently
        # `inspect.currentframe().f_back.f_back` would have worked, but we have
        # no guarantee that it'll remain like this forever.
        @contextmanager
        def cm():
            old_local_names = set(frame.f_locals.keys())
            yield
            new_locals = frame.f_locals
            with ExitStack() as stack:
                if header:
                    stack.enter_context(self.indented(header, *args, footer=False, **kwargs))
                # Traverse co_varnames to retain order
                for name in frame.f_code.co_varnames:
                    if name not in old_local_names and name in new_locals:
                        self.info('%s = %s', name, new_locals[name])

                # Print the names we somehow missed(because they weren't in co_varnames - it can happen!)
                for name in (new_locals.keys() - old_local_names - set(frame.f_code.co_varnames)):
                    self.info('%s = %s', name, new_locals[name])

        return cm()


def log_context(method=None, **ctx):
    if not method:
        return partial(log_context, **ctx)

    sig = inspect.signature(method)

    @wraps(method)
    def inner(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        context = {k: fmt.format(**bound.arguments) for k, fmt in ctx.items()}
        with THREAD_LOGGING_CONTEXT(context):
            return method(*args, **kwargs)
    return inner


# =================================================================

def initialize(*, graphical=AUTO, coloring=AUTO, indentation=0, context={}, patch=False, framework="logging"):
    """
    Initialize easypy's logging module.
    Also injects easypy's ContextableLoggerMixin into the builtin logging module.

    :param graphical: Whether to use unicode or ascii for graphical elements
    :param coloring: Whether to use color in logging
    :param indentation: The initial indentation level
    :param context: The initial logging context attributes
    :param patch: Whether to monkey-patch the logging framework so that it uses easypy's context tracking feature
    :param framework: specify which framework is in use - ``'logging'`` or ``'logbook'``
    """

    if G.initialized:
        logging.warning("%s is already initialized", __name__)
        return

    G.IS_A_TTY = sys.stdout.isatty()

    # =====================
    # Graphics initialization

    G.GRAPHICAL = if_auto(graphical, G.IS_A_TTY)
    G.graphics = Graphics.Graphical if G.GRAPHICAL else Graphics.ASCII

    # =====================
    # Coloring indentation

    G.COLORING = if_auto(coloring, G.IS_A_TTY)
    if G.COLORING:
        from easypy.colors import RED, GREEN, BLUE, WHITE, DARK_GRAY
        G.INDENT_COLORS = [
            ("DARK_%s<<{}>>" % color.upper()).format
            for color in "GREEN BLUE MAGENTA CYAN YELLOW".split()]
        random.shuffle(G.INDENT_COLORS)
    else:
        RED = GREEN = BLUE = WHITE = DARK_GRAY = lambda txt, *_, **__: txt
        G.INDENT_COLORS = [lambda s: s]

    G.RED = RED
    G.GREEN = GREEN
    G.BLUE = BLUE
    G.WHITE = WHITE
    G.DARK_GRAY = DARK_GRAY

    # =====================
    # Context

    G._ctx = ExitStack()
    G._ctx.enter_context(THREAD_LOGGING_CONTEXT(indentation=indentation, **context))

    # =====================
    # Mixin injection
    from .heartbeats import HeartbeatHandlerMixin
    global HeartbeatHandler, EasypyLogger, get_console_handler, ConsoleFormatter
    global ThreadControl
    global _get_logger

    if framework == "logging":
        from .progressbar import ProgressBarLoggerMixin
        from .plumbum import PlumbumPipeLoggerMixin
        from ._logging import get_console_handler, LEVEL_COLORS, patched_makeRecord, ConsoleFormatter
        from ._logging import ThreadControl, SilentExceptionLoggerMixin
        G.LEVEL_COLORS = LEVEL_COLORS

        logging.INFO1 = logging.INFO + 1
        logging.addLevelName(logging.INFO1, "INFO1")
        G.NOTICE = logging.INFO1

        class ContextLoggerMixin(ContextableLoggerMixin, ProgressBarLoggerMixin, PlumbumPipeLoggerMixin):
            # for backwards compatibility
            def notice(self, *args, **kwargs):
                return self.log(G.NOTICE, *args, **kwargs)

            info1 = notice  # for backwards compatibility

        class EasypyLogger(logging.Logger, ContextableLoggerMixin, SilentExceptionLoggerMixin):
            pass

        _get_logger = logging.getLogger

        if patch:
            logging.Logger._makeRecord, logging.Logger.makeRecord = logging.Logger.makeRecord, patched_makeRecord
            logging.setLoggerClass(EasypyLogger)
            logging.Logger.manager.setLoggerClass(EasypyLogger)

        class HeartbeatHandler(logging.Handler, HeartbeatHandlerMixin):
            pass

    elif framework == "logbook":
        import logbook
        from ._logbook import ContextProcessor, ThreadControl, ConsoleHandlerMixin
        from ._logbook import get_console_handler, LEVEL_COLORS, ConsoleFormatter
        from ._logbook import ConvertsFormatString, SilentExceptionLoggerMixin
        G.LEVEL_COLORS = LEVEL_COLORS
        G.NOTICE = logbook.NOTICE

        class HeartbeatHandler(logbook.Handler, HeartbeatHandlerMixin):
            pass

        class EasypyLogger(logbook.Logger, ContextableLoggerMixin, SilentExceptionLoggerMixin):
            pass

        class InternalEasypyLogger(ConvertsFormatString, EasypyLogger):
            pass

        _get_logger = InternalEasypyLogger

        if patch:
            ContextProcessor().push_application()
            ThreadControl().push_application()
            logbook.StderrHandler.__bases__ = logbook.StderrHandler.__bases__ + (ConsoleHandlerMixin,)
            logbook.Logger.__bases__ = logbook.Logger.__bases__ + (ContextableLoggerMixin,)

    else:
        raise NotImplementedError("No support for %s as a logging framework" % framework)

    import gc
    from .._logger_init import DeferredEasypyLogger
    for obj in gc.get_objects():
        if isinstance(obj, DeferredEasypyLogger):
            obj.logger = _get_logger(name=obj.name)
    DeferredEasypyLogger._get_logger = _get_logger

    G.initialized = True
