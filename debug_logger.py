import logging

# import this module to dump colories DEBUG level logging on stdout
#
# includes thread info by default, so can be useful for some
# quick thread debugging (hahaha...)
#

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

    FORMAT = (u"""$BOLD[%(levelname)s]$RESET """
              """%(asctime)-15s """
#              """\033[1;35m%(name)s$RESET """
#              """%(processName)s """
              """[tid: \033[32m%(thread)d$RESET tname:\033[32m%(threadName)s]$RESET """
#              """%(module)s """
              """@%(filename)s"""
#              """%(funcName)s()"""
              """:%(lineno)d """
              """- %(message)s""")
              #              """- $BOLD%(message)s$RESET""")


    COLORS = {
        'WARNING': YELLOW,
        'INFO': YELLOW,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }
    # \ x 1 b [ 38 ; 5; 231m
    THREAD_COLORS = dict((color_number, color_seq) for \
                         (color_number, color_seq) in [(x, "\033[38;5;%dm" % (x+16)) for x in range(220)])

    #print THREAD_COLORS
    #print "foo %s slip %s blip %s" % (THREAD_COLORS[0], THREAD_COLORS[1], RESET_SEQ)
    def formatter_msg(self, msg, use_color=True):
        # do color stuff here if we want $RED in format string
        if use_color:
            msg = msg.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)
        else:
            msg = msg.replace("$RESET", "").replace("$BOLD", "")
        return msg

    def __init__(self, use_color=True):
        msg = self.formatter_msg(self.FORMAT, use_color)
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

        self.thread_counter = 0
        self.use_thread_color = False

    def get_thread_color(self, threadid):
        thread_mod = threadid % 220
        #print threadid, thread_mod % 220
        return self.THREAD_COLORS[thread_mod]

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in self.COLORS:
            fore_color = 30 + self.COLORS[levelname]
            levelname_color = self.COLOR_SEQ % fore_color + levelname + self.RESET_SEQ
            record.levelname = levelname_color
        if self.use_color and self.use_thread_color:
            fore_color_seq = self.get_thread_color(record.thread)
        #    print "%s foo %s%s" % (fore_color_seq, record.msg, self.RESET_SEQ)
            msg = "%s%s%s" % (fore_color_seq, record.msg, self.RESET_SEQ)
            #msg = "%s%s%s" % ('', record.msg, '')
            record.msg = msg
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

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().addHandler(_get_handler())
