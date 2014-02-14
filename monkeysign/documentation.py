# -*- coding: utf-8 -*-

"""build_manpage command -- Generate man page from setup()"""

import os
import datetime
from distutils.command.build import build
from distutils.core import Command
from distutils.errors import DistutilsOptionError
import optparse


class build_manpage(Command):

    description = 'Generate man page from setup().'

    user_options = [
        ('output=', 'O', 'output directory'),
        ('parsers=', None, 'module path to optparser (e.g. command:mymod:func)'),
        ]

    def initialize_options(self):
        self.output = None
        self.parsers = None

    def finalize_options(self):
        if self.output is None:
            raise DistutilsOptionError('\'output\' option is required')
        if self.parsers is None:
            raise DistutilsOptionError('\'parser\' option is required')
        self._today = datetime.date.today()
        self._parsers = []
        for parser in self.parsers.split():
            scriptname, mod_name, func_name = parser.split(':')
            fromlist = mod_name.split('.')
            try:
                class_name, func_name = func_name.split('.')
            except ValueError:
                class_name = None
            mod = __import__(mod_name, fromlist=fromlist)
            if class_name is not None:
                cls = getattr(mod, class_name)
                parser = getattr(cls, func_name)()
            else:
                parser = getattr(mod, func_name)()
            parser.formatter = ManPageFormatter()
            parser.formatter.set_parser(parser)
            parser.prog = scriptname
            self._parsers.append(parser)

    def _markup(self, txt):
        return txt.replace('-', '\\-')

    def _write_header(self, parser):
        appname = parser.prog
        ret = []
        ret.append('.TH %s 1 %s\n' % (self._markup(appname),
                                      self._today.strftime('%Y\\-%m\\-%d')))
        description = parser.get_description()
        if description:
            name = self._markup('%s - %s' % (self._markup(appname),
                                             description.splitlines()[0]))
        else:
            name = self._markup(appname)
        ret.append('.SH NAME\n%s\n' % name)
        # override argv, we need to format it later
        prog_bak = parser.prog
        parser.prog = ''
        synopsis = parser.get_usage().lstrip(' ')
        parser.prog = prog_bak
        if synopsis:
            ret.append('.SH SYNOPSIS\n.B %s\n%s\n' % (self._markup(appname),
                                                      synopsis))
        long_desc = parser.get_description()
        if long_desc:
            ret.append('.SH DESCRIPTION\n%s\n' % self._markup("\n".join(long_desc.splitlines()[1:])))
        return ''.join(ret)

    def _write_options(self, parser):
        ret = ['.SH OPTIONS\n']
        ret.append(parser.format_option_help())
        return ''.join(ret)

    def _write_footer(self, parser):
        ret = []
        appname = self.distribution.get_name()
        author = '%s <%s>' % (self.distribution.get_author(),
                              self.distribution.get_author_email())
        ret.append(('.SH AUTHORS\n.B %s\nwas written by %s.\n'
                    % (self._markup(appname), self._markup(author))))
        homepage = self.distribution.get_url()
        ret.append(('.SH DISTRIBUTION\nThe latest version of %s may '
                    'be downloaded from\n'
                    '.UR %s\n.UE\n'
                    % (self._markup(appname), self._markup(homepage),)))
        return ''.join(ret)

    def run(self):
        for parser in self._parsers:
            manpage = []
            manpage.append(self._write_header(parser))
            manpage.append(self._write_options(parser))
            manpage.append(self._write_footer(parser))
            try:
                os.mkdir(self.output)
            except OSError:
                # ignore already existing directory
                pass
            path = os.path.join(self.output, parser.prog + '.1')
            self.announce('writing man page to %s' % path, 2)
            stream = open(path, 'w')
            stream.write(''.join(manpage))
            stream.close()


class ManPageFormatter(optparse.HelpFormatter):

    def __init__(self,
                 indent_increment=2,
                 max_help_position=24,
                 width=None,
                 short_first=1):
        optparse.HelpFormatter.__init__(self, indent_increment,
                                        max_help_position, width, short_first)

    def _markup(self, txt):
        return txt.replace('-', '\\-')

    def format_usage(self, usage):
        return self._markup(usage)

    def format_heading(self, heading):
        if self.level == 0:
            return ''
        return '.TP\n%s\n' % self._markup(heading.upper())

    def format_option(self, option):
        result = []
        opts = self.option_strings[option]
        result.append('.TP\n.B %s\n' % self._markup(opts))
        if option.help:
            help_text = '%s\n' % self._markup(self.expand_default(option))
            result.append(help_text)
        return ''.join(result)

class build_slides(Command):

    description = 'Generate the HTML presentation with rst2s5.'

    user_options = [
        ('file=', 'f', 'rst file'),
        ]

    def initialize_options(self):
        self.file = None

    def finalize_options(self):
        if self.file is None:
            raise DistutilsOptionError('\'file\' option is required')

    def run(self):
        html = os.path.join(os.path.dirname(self.file), os.path.splitext(os.path.basename(self.file))[0] + '.html')
        self.announce('processing slides from %s to %s' % (self.file, html), 2)
        os.system('rst2s5 --theme default "%s" "%s"' % (self.file, html))

# (function, predicate), see http://docs.python.org/2/distutils/apiref.html#distutils.cmd.Command.sub_commands
build.sub_commands.append(('build_manpage', None))
build.sub_commands.append(('build_slides', None))
