# This will be deprecated since it will be available in Plumbum
from easypy.tokens import AUTO, if_auto


class PlumbumPipeLoggerMixin():
    INFO = "INFO"
    DEBUG = "DEBUG"

    def __ror__(self, cmd):
        """
        Integration with plumbum's command objects for subprocess execution.
        Pipe stderr and stdout lines into this logger (at level INFO)
        """
        return cmd | self.pipe(self.INFO, self.INFO)

    __rand__ = __ror__  # for backwards compatibility

    def pipe(self, err_level=AUTO, out_level=AUTO, prefix=None, line_timeout=10 * 60, **kw):
        """
        Integration with plumbum's command objects for subprocess execution.
        Pipe stderr and stdout lines into this logger (at levels `err_level/out_level`)
        Optionally use `prefix` for each line.
        """
        err_level = if_auto(err_level, self.DEBUG)
        out_level = if_auto(out_level, self.INFO)

        class LogPipe(object):
            def __ror__(_, cmd):
                popen = cmd if hasattr(cmd, "iter_lines") else cmd.popen()
                for out, err in popen.iter_lines(line_timeout=line_timeout, **kw):
                    for level, line in [(out_level, out), (err_level, err)]:
                        if not line:
                            continue
                        for l in line.splitlines():
                            if prefix:
                                l = "%s: %s" % (prefix, l)
                            self.log(level, l)
                return popen.returncode
            __rand__ = __ror__  # for backwards compatibility

        return LogPipe()

    def pipe_info(self, prefix=None, **kw):
        """
        Integration with plumbum's command objects for subprocess execution.
        Pipe stderr and stdout lines into this logger (both at level INFO)
        """
        return self.pipe(self.INFO, self.INFO, prefix=prefix, **kw)

    def pipe_debug(self, prefix=None, **kw):
        """
        Integration with plumbum's command objects for subprocess execution.
        Pipe stderr and stdout lines into this logger (both at level DEBUG)
        """
        return self.pipe(self.DEBUG, self.DEBUG, prefix=prefix, **kw)
