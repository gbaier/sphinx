# -*- coding: utf-8 -*-
"""
    sphinx.util.pycompat
    ~~~~~~~~~~~~~~~~~~~~

    Stuff for Python version compatibility.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import io
import sys
import codecs
import warnings

from six import PY3, class_types, text_type, exec_
from six.moves import zip_longest
from itertools import product

from sphinx.deprecation import RemovedInSphinx16Warning

if False:
    # For type annotation
    from typing import Any, Callable  # NOQA


NoneType = type(None)

# ------------------------------------------------------------------------------
# Python 2/3 compatibility

# prefix for Unicode strings
if PY3:
    u = ''
else:
    u = 'u'


# TextIOWrapper
if PY3:
    from io import TextIOWrapper
else:
    def TextIOWrapper(stream, encoding):
        # type: (file, str) -> unicode
        return codecs.lookup(encoding or 'ascii')[2](stream)


# sys_encoding: some kind of default system encoding; should be used with
# a lenient error handler
if PY3:
    sys_encoding = sys.getdefaultencoding()
else:
    sys_encoding = __import__('locale').getpreferredencoding()


# terminal_safe(): safely encode a string for printing to the terminal
if PY3:
    def terminal_safe(s):
        # type: (unicode) -> unicode
        return s.encode('ascii', 'backslashreplace').decode('ascii')
else:
    def terminal_safe(s):
        # type: (unicode) -> unicode
        return s.encode('ascii', 'backslashreplace')


# convert_with_2to3():
if PY3:
    # support for running 2to3 over config files
    def convert_with_2to3(filepath):
        # type: (unicode) -> unicode
        from lib2to3.refactor import RefactoringTool, get_fixers_from_package
        from lib2to3.pgen2.parse import ParseError
        fixers = get_fixers_from_package('lib2to3.fixes')
        refactoring_tool = RefactoringTool(fixers)
        source = refactoring_tool._read_python_source(filepath)[0]
        try:
            tree = refactoring_tool.refactor_string(source, 'conf.py')
        except ParseError as err:
            # do not propagate lib2to3 exceptions
            lineno, offset = err.context[1]
            # try to match ParseError details with SyntaxError details
            raise SyntaxError(err.msg, (filepath, lineno, offset, err.value))
        return text_type(tree)
else:
    # no need to refactor on 2.x versions
    convert_with_2to3 = None  # type: ignore


# htmlescape()
if PY3:
    from html import escape as htmlescape
else:
    from cgi import escape as htmlescape  # NOQA


# UnicodeMixin
if PY3:
    class UnicodeMixin(object):
        """Mixin class to handle defining the proper __str__/__unicode__
        methods in Python 2 or 3."""

        def __str__(self):
            return self.__unicode__()
else:
    class UnicodeMixin(object):
        """Mixin class to handle defining the proper __str__/__unicode__
        methods in Python 2 or 3."""

        def __str__(self):
            return self.__unicode__().encode('utf8')


# indent()
if PY3:
    from textwrap import indent
else:
    # backport from python3
    def indent(text, prefix, predicate=None):
        # type: (unicode, unicode, Callable) -> unicode
        if predicate is None:
            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)
        return ''.join(prefixed_lines())


def execfile_(filepath, _globals, open=open):
    # type: (unicode, Any, Callable) -> None
    from sphinx.util.osutil import fs_encoding
    # get config source -- 'b' is a no-op under 2.x, while 'U' is
    # ignored under 3.x (but 3.x compile() accepts \r\n newlines)
    mode = 'rb' if PY3 else 'rbU'
    with open(filepath, mode) as f:
        source = f.read()

    # py26 accept only LF eol instead of CRLF
    if sys.version_info[:2] == (2, 6):
        source = source.replace(b'\r\n', b'\n')

    # compile to a code object, handle syntax errors
    filepath_enc = filepath.encode(fs_encoding)
    try:
        code = compile(source, filepath_enc, 'exec')
    except SyntaxError:
        if convert_with_2to3:
            # maybe the file uses 2.x syntax; try to refactor to
            # 3.x syntax using 2to3
            source = convert_with_2to3(filepath)
            code = compile(source, filepath_enc, 'exec')
        else:
            raise
    exec_(code, _globals)

# ------------------------------------------------------------------------------
# Internal module backwards-compatibility


class _DeprecationWrapper(object):
    def __init__(self, mod, deprecated):
        # type: (Any, Dict) -> None
        self._mod = mod
        self._deprecated = deprecated

    def __getattr__(self, attr):
        if attr in self._deprecated:
            warnings.warn("sphinx.util.pycompat.%s is deprecated and will be "
                          "removed in Sphinx 1.6, please use the standard "
                          "library version instead." % attr,
                          RemovedInSphinx16Warning, stacklevel=2)
            return self._deprecated[attr]
        return getattr(self._mod, attr)


sys.modules[__name__] = _DeprecationWrapper(sys.modules[__name__], dict(  # type: ignore
    zip_longest = zip_longest,
    product = product,
    all = all,
    any = any,
    next = next,
    open = open,
    class_types = class_types,
    base_exception = BaseException,
    relpath = __import__('os').path.relpath,
    StringIO = io.StringIO,
    BytesIO = io.BytesIO,
))
