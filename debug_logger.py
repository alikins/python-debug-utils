import logging
import re
import sys

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

    '%(_cdl_process)s%(process)d%(_cdl_reset)s %(_cdl_threadName)%(threadName)s%(_cdl_reset)s - %(msg)'

    Note that adding those log record attributes is left to... <FIXME>.
    '''

    color_attrs = ['name', 'process', 'processName', 'levelname', 'threadName', 'thread', 'message', 'exc_text']

    color_attrs_string = '|'.join(color_attrs)

    re_string = "(?P<full_attr>%\((?P<attr_name>" + color_attrs_string + "?)\).*?[dsf])"

    color_format_re = re.compile(re_string)

    replacement = "%(_cdl_\g<attr_name>)s\g<full_attr>%(_cdl_unset)s"

    exc_info_post = '%(exc_text_sep)s%(exc_text)s'
    format_string = '%s%s' % (format_string, exc_info_post)
    format_string = color_format_re.sub(replacement, format_string)

    #format_string = "%(_cdl_default)s" + format_string + "%(_cdl_reset)s"

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

    FORMAT = ("""%(asctime)-15s %(relativeCreated)d """
              """%(levelname)-8s """
#              """\033[1;35m%(name)s$RESET """
#              """%(processName)s """
              """%(processName)-15s %(_cdl_process)spid=%(process)5d """
              """%(_cdl_thread)stid=%(thread)d %(_cdl_threadName)stname=%(threadName)-15s """
              #              """[tid: \033[32m%(thread)d$RESET tname:\033[32m%(threadName)s]$RESET """
#              """%(module)s """
              """[%(name)s] """
              """@%(filename)s"""
#              """%(funcName)s()"""
              """:%(lineno)-4d """
              """- %(_cdl_thread)s%(message)s%(_cdl_reset)s""")
#              """- $BOLD%(message)s$RESET""")

    COLORS = {
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }

    BASE_COLORS = dict((color_number, color_seq) for
                       (color_number, color_seq) in [(x, "\033[38;5;%dm" % x) for x in range(8)])
    # \ x 1 b [ 38 ; 5; 231m
    THREAD_COLORS = dict((color_number, color_seq) for
                         (color_number, color_seq) in [(x, "\033[38;5;%dm" % (x + 16)) for x in range(220)])

    LEVEL_COLORS = {'TRACE': BASE_COLORS[BLUE],
                    'SUBDEBUG': BASE_COLORS[BLUE],
                    'DEBUG': BASE_COLORS[BLUE],
                    'INFO': BASE_COLORS[GREEN],
                    'SUBWARNING': BASE_COLORS[YELLOW],
                    'WARNING': BASE_COLORS[YELLOW],
                    'ERROR': BASE_COLORS[RED],
                    # bold red?
                    'CRITICAL': BASE_COLORS[RED]}
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

        self.default_color = self.BASE_COLORS[self.WHITE]
        #self.default_color = self.BASE_COLORS[self.YELLOW]

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
    # TODO: this could be own class/methods like ContextColor(log_record) that returns color info
    def get_thread_color(self, threadid):
        # 220 is useable 256 color term color (forget where that comes from? some min delta-e division of 8x8x8 rgb colorspace?)
        thread_mod = threadid % 220
        #print threadid, thread_mod % 220
        return self.THREAD_COLORS[thread_mod]

    # TODO: This could special case 'MainThread'/'MainProcess' to pick a good predictable color
    def get_name_color(self, name):
        name_hash = hash(name)
        name_mod = name_hash % 220
        return self.THREAD_COLORS[name_mod]

    def get_level_color(self, levelname):
        if levelname not in self.LEVEL_COLORS:
            return
        level_color = self.LEVEL_COLORS[levelname]
        return level_color

    def get_process_colors(self, pname, pid, tname, tid):
        '''Given process/thread info, return reasonable colors for them.

        Roughly:

            - attempts to get a unique color per processName
            - attempts to get a unique color per pid
                - attempt to make those the same for MainProcess
                - any other processName, the pname color and the pid color cann be different
            - if threadName is 'MainThread', make tname_color and tid_color match MainProcess pname_color and pid_color
            - other threadNames get a new color and new tid_color

            Existing get_*color_ methods attempt to divy up colors by mod 220 on tid/pid, or mod 220 on hash of thread or pid name
            NOTE: This doesn't track any state so there is no ordering or prefence to the colors given out.
        '''
        #pprint.pprint(self._efmt)
        pname_color = self.get_name_color(pname)
        if pname == 'MainProcess':
            pid_color = pname_color
        else:
            pid_color = self.get_thread_color(pid)

        if tname == 'MainThread':
            #tname_color = pname_color
            tname_color = pid_color
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

        # 'cdl' is 'context debug logger'. Mostly just an unlikely record name to avod name collisions.
        record._cdl_reset = self.RESET_SEQ
        record._cdl_default = self.default_color
        record._cdl_unset = self.default_color
        record.exc_text_sep = ''
        record.exc_text = ''

        # NOTE: the impl here is based on info from justthe LogRecord and should be okay across threads
        #       If this wants to use more global data, beware...
        if self.use_color:
            level_color = self.get_level_color(record.levelname)
            record._cdl_levelname = level_color
            record._cdl_name = self.get_name_color(record.name)

        if self.use_color and self.use_thread_color:
            pname_color, pid_color, tname_color, tid_color = self.get_process_colors(record.processName, record.process, record.threadName, record.thread)

            # NOTE: and here is where we currently mutate the existing log record (we add attributes to it).
            # TODO: create a new/copy LogRecord, and only use it to pass to our use of logging.Formatter.format()
            record._cdl_process = pid_color
            record._cdl_processName = pname_color
            record._cdl_thread = tid_color
            record._cdl_threadName = tname_color
            record._cdl_exc_text = record._cdl_thread

        record._cdl_default = record._cdl_process
        record._cdl_message = record._cdl_default

        #record._cdl_exc_text = self.BASE_COLORS[self.YELLOW]
        if record.exc_info:
            record.exc_text_sep = '\n'

        return self._format(record)

    # format is based on from stdlib python logging.LogFormatter.format()
    # It's kind of a pain to customize exception formatting, since it
    # just appends the exception string from formatException() to the formatted message.
    def _format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
            #record.exc_text_placeholder = '\n'

        #import pprint
        #print('self._fmt=%s' % self._fmt)
        #print('record.__dict__=')
        #pprint.pprint(record.__dict__)
        s = self._fmt % record.__dict__
        return s

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
