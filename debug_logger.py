import logging

# import this module to dump colories DEBUG level logging on stdout
#
# includes thread info by default, so can be useful for some
# quick thread debugging (hahaha...)
#

# TODO: add a Filter or LoggingAdapter that adds a record attribute for parent pid
#       (and maybe thread group/process group/cgroup ?)


def context_color_format_string(format_string):
    '''For extending a format string for logging.Formatter to include attributes with color info.

    ie, '%(process)d %(threadName)s - %(msg)'

    becomes

    '%(_dlc_process)s%(process)d%(_dlc_reset)s %(_dlc_threadName)%(threadName)s%(_dlc_reset)s - %(msg)'

    Note that adding those log record attributes is left to... <FIXME>.
    '''
    c_attrs = [('%(process)d', 'process'),
                ('%(processName)s', 'processName'),
                ('%(thread)d', 'thread'),
                ('%(threadName)s', 'threadName')]

    for c_attr, c_attr_short in c_attrs:
        format_string = format_string.replace(c_attr, '%%(_dlc_%s)s%s%%(reset)s' % (c_attr_short, c_attr))

    return format_string


class ColorFormatter(logging.Formatter):
    FORMAT = ("[$BOLD%(name)-20s$RESET][%(levelname)-18s]  "
              "%(message)s "
              "($BOLD%(filename)s$RESET:%(lineno)d)")

    # hacky ansi color stuff
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    funcName = u""
    processName = u""

    FORMAT = (u"""[%(levelname)s] """
              """%(asctime)-15s """
#              """\033[1;35m%(name)s$RESET """
#              """%(processName)s """
              """%(processName)s %(process)d """
              """[tid: %(thread)d tname:%(threadName)s """
              #              """[tid: \033[32m%(thread)d$RESET tname:\033[32m%(threadName)s]$RESET """
#              """%(module)s """
              """@%(filename)s"""
#              """%(funcName)s()"""
              """:%(lineno)d """
              """- %(_dlc_threadName)sthread_name_color%(reset)s %(message)s""")
#              """- $BOLD%(message)s$RESET""")

    COLORS = {
        'WARNING': YELLOW,
        'INFO': YELLOW,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }
    # \ x 1 b [ 38 ; 5; 231m
    THREAD_COLORS = dict((color_number, color_seq) for
                         (color_number, color_seq) in [(x, "\033[38;5;%dm" % (x + 16)) for x in range(220)])

    #print THREAD_COLORS
    #print "foo %s slip %s blip %s" % (THREAD_COLORS[0], THREAD_COLORS[1], RESET_SEQ)
    # TODO: -> transform_format_string
    #       expand format sting to include color record attributes, and let self.format add/tweak the attributes
    # note: python-coloredlogs ColoredFormatter does something similar
    def formatter_msg(self, fmt, use_color=True):
        # do color stuff here if we want $RED in format string
        # if auto_format: ?
        # TODO: transform '%(thread)d' -> '%(threadColor)s%(thread)d%(reset)s'
        if use_color:
            fmt = fmt.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
        else:
            fmt = fmt.replace("$RESET", "").replace("$BOLD", "")
        return fmt

    # A little weird...
    @property
    def _fmt(self):
        if not self._color_fmt:
            self._color_fmt = context_color_format_string(self._base_fmt)
        return self._color_fmt

    @_fmt.setter
    def _fmt(self, value):
        self._base_fmt = value
        self._color_fmt = None

    def __init__(self, fmt=None, use_color=True):
        fmt = fmt or self.FORMAT
        logging.Formatter.__init__(self, fmt)
        self._base_fmt = fmt
        self.use_color = use_color

        self.thread_counter = 0
        self.use_thread_color = False

    # TODO: rename and generalize
    # TODO: tie tid/threadName and process/processName together so they start same color
    #       so MainProcess, the first pid/processName are same, and maybe MainThread//first tid
    # DOWNSIDE: requires tracking all seen pid/process/tid/threadName ? that could be odd with multi-processes with multi instances
    #           of the Formatter
    # TODO: make so a given first ProcessName will always start the same color (so multiple runs are consistent)
    # TODO: make 'msg' use the most specific combo of pid/processName/tid/threadName
    # TODO: generalize so it will for logger name as well
    # MAYBE: color hiearchy for logger names? so 'foo.model' and 'foo.util' are related...
    #        maybe split on '.' and set initial color based on hash of sub logger name?
    # SEEALSO: chromalog module does something similar, may be easiest to extend
    def get_thread_color(self, threadid):
        # 220 is useable 256 color term color (forget where that comes from? some min delta-e division of 8x8x8 rgb colorspace?)
        thread_mod = threadid % 220
        #print threadid, thread_mod % 220
        return self.THREAD_COLORS[thread_mod]

    def get_name_color(self, name):
        name_hash = hash(name)
        name_mod = name_hash % 220
        return self.THREAD_COLORS[name_mod]

    def get_process_colors(self, pname, pid, tname, tid):
        #pprint.pprint(self._efmt)
        pname_color = self.get_name_color(pname)
        if pname == 'MainProcess':
            pid_color = pname_color
        else:
            pid_color = self.get_thread_color(pid)

        if tname == 'MainThread':
            tname_color = pname_color
            tid_color = tname_color
        else:
            tname_color = self.get_name_color(tname)
            tid_color = self.get_thread_color(tid)

        return pname_color, pid_color, tname_color, tid_color

    # TODO: maybe add a Filter that sets a record attribute for process/pid/thread/tid color that formatter would use
    #       (that would let formatter string do '%(theadNameColor)s tname=%(threadName)s %(reset)s %(processColor)s pid=%(process)d%(reset)s'
    #       so that the entire blurb about process info matches instead of just the attribute
    #       - also allows format to just expand a '%(threadName)s' in fmt string to '%(theadNameColor)s%(threadName)s%(reset)s' before regular formatter
    # DOWNSIDE: Filter would need to be attach to the Logger not the Handler
    def format(self, record):
        record.reset = self.RESET_SEQ
        levelname = record.levelname

        if self.use_color and levelname in self.COLORS:
            fore_color = 30 + self.COLORS[levelname]
            levelname_color = self.COLOR_SEQ % fore_color + levelname + self.RESET_SEQ
            record.levelname = levelname_color

        if self.use_color and self.use_thread_color:
            thread_color = self.get_thread_color(record.thread)
            process_color = self.get_thread_color(record.process)
            #pname_color, pid_color = self.get_process_colors(record.processName, record.process)
            pname_color, pid_color, tname_color, tid_color = self.get_process_colors(record.processName, record.process, record.threadName, record.thread)
            record._dlc_process = pid_color
            record._dlc_processName = pname_color
            record._dlc_thread = tid_color
            record._dlc_threadName =tname_color
        #    print "%s foo %s%s" % (fore_color_seq, record.msg, self.RESET_SEQ)
            #record.threadName = "%s%s%s" % (fore_color_seq, record.threadName, self.RESET_SEQ)
            #record._dlc_threadName = self.get_name_color(record.threadName)
            #record._dlc_thread = thread_color
            #msg = "%s%s%s" % (fore_color_seq, record.msg, self.RESET_SEQ)
            #msg = "%s%s%s" % ('', record.msg, '')
            #record.msg = msg

        return logging.Formatter.format(self, record)


def _get_handler():
    #%(asctime)s tid:%(thread)d
    #fmt = u'\033[33m**: tname:%(threadName)s @%(filename)s:%(lineno)d - %(message)s\033[0m'
#    fmt = u': tname:%(threadName)s @%(filename)s:%(lineno)d - %(message)s'
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(use_color=True))
    #handler.setFormatter(logging.Formatter(fmt))
    handler.setLevel(logging.DEBUG)

    return handler

#logging.getLogger().setLevel(logging.DEBUG)
#logging.getLogger().addHandler(_get_handler())
