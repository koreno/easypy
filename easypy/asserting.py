import re
from inspect import currentframe


class AssertionBuilder(object):
    _pattern = re.compile(r'`(.+?)`')
    _expr_pattern = re.compile(r'^(.*?)([:|])(.+?)$')
    _not_available = object()

    def __init__(self, source):
        self.source = source
        self.expr_parts = []
        self.format_parts = []
        self.expr_results = []
        self.parse_assertion(source)

    def parse_assertion(self, source):
        prev_end = 0
        for match in self._pattern.finditer(source):
            start, end = match.span()
            self.expr_parts.append(source[prev_end:start])
            self.format_parts.append(source[prev_end:start])
            self.parse_expr(match.group(1))
            prev_end = end

    def parse_expr(self, expr):
        index = None
        match = self._expr_pattern.match(expr)
        if match:
            caption, format_type, expr = match.groups()
            if format_type == '|':
                self.format_parts.append(caption)
            elif format_type == ':':
                index = len(self.expr_results)
                self.format_parts.append((self.format_expr_result, index, caption or expr))
            else:
                assert False, 'format_type is %r - expected : or |' % (format_type,)
        else:
            index = len(self.expr_results)
            self.format_parts.append((self.format_expr_result, index))

        if index is None:
            self.expr_parts.append(expr)
        else:
            self.expr_results.append(self._not_available)
            self.expr_parts.append('__set_expr_result(%s, (%s))' % (index, expr))

    def format_expr_result(self, index, caption=None):
        expr_result = self.expr_results[index]
        if expr_result is self._not_available:
            expr_result = '#N/A'
        else:
            expr_result = repr(expr_result)

        if caption is None:
            return expr_result
        else:
            return '%s(%s)' % (caption, expr_result)

    def eval_for(self, frame):
        frame_locals = {'__set_expr_result': self.set_expr_result}
        frame_locals.update(**frame.f_locals)
        return eval(''.join(self.expr_parts), frame.f_globals, frame_locals)

    def set_expr_result(self, index, value):
        self.expr_results[index] = value
        return value

    def format_message(self):
        def generator():
            for part in self.format_parts:
                if isinstance(part, str):
                    yield part
                else:
                    yield part[0](*part[1:])
        return ''.join(generator())


def ASSERT(assertion):
    frame = currentframe().f_back
    assertion_builder = AssertionBuilder(assertion)
    result = assertion_builder.eval_for(frame)
    assert result, assertion_builder.format_message()
