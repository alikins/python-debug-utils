
# module to trace some basic io calls
#
# less noisy than strace, logs calls originating
# from python code only
#
# wrap the built in open and log it's use
#
import __builtin__

import atexit
import inspect
from collections import defaultdict


origopen = __builtin__.open

open_callback = None
# set to None if you dont want info as each open happens, but only report
def open_callback(filename, mode, module, lineno, function, code_context, index):
    print "%s %s %s:%s %s" % (filename, mode, module, lineno, function)

import os
pwd = os.path.normpath(os.getcwd())


def find_useful_frame(stack):
    # try to find a frame that points back to our code
    for frame in stack[1:]:
        if frame[1].startswith(pwd):

            return frame


open_dict = defaultdict(list)


def newopen(*args, **kwargs):
    filename = args[0]
    mode = ""
    if len(args) > 1:
        mode = args[1]

    __builtin__.open = origopen

    # some stack fidgiting to try to get a useful module and filename,
    # aka, the module that called open(), not open itself
    frame_records = inspect.stack()
    useful_frame = find_useful_frame(frame_records)
    #print useful_frame
    # frames is ordered from down->up, grab next frame up
    calling_frame = frame_records[1]
    calling_frame = useful_frame
    (module, lineno, function, code_context, index) = inspect.getframeinfo(calling_frame[0])
    open_dict[filename].append((mode, module, lineno, function, code_context, index))

    if open_callback:
        open_callback(filename, mode, module, lineno, function, code_context, index)

    # monkeypatch open()
    __builtin__.open = newopen
    return origopen(*args, **kwargs)

__builtin__.open = newopen


# set to None to only see the report
def open_report():
    for filename in open_dict:
        print filename
        for callers in open_dict[filename]:
            print "\t%s:%s %s" % (callers[1], callers[2], callers[3])
        print

# clearly, these guys could be generalized, but this is a kluge, not
# a tracing framework

import socket
orig_socket = socket.socket


def connect_callback(hostname, port, module, lineno, function, code_context, index):
    print "%s:%s %s:%s %s" % (hostname, port, module, lineno, function)


socket_connect_dict = defaultdict(list)


def connect_report():
    for hostname in socket_connect_dict:
        print hostname
        for callers in socket_connect_dict[hostname]:
            print "\t%s %s:%s %s" % (callers[0], callers[1], callers[2], callers[3])
        print


class LogSocket(socket.socket):
    def connect(self, *args, **kwargs):
        #print "socket connect args", args, kwargs
        frame_records = inspect.stack()
        calling_frame = frame_records[1]
        useful_frame = find_useful_frame(frame_records)
        calling_frame = useful_frame
        #print "frame_records", frame_records
        #print "calling_frame", calling_frame
        (module, lineno, function, code_context, index) = inspect.getframeinfo(calling_frame[0])
        host = args[0][0]
        port = args[0][1]
        socket_connect_dict[host].append((port, module, lineno, function, code_context, index))

        if connect_callback:
            connect_callback(host, port, module, lineno, function, code_context, index)

        # wrap socket.connect, probably any number of better ways to do this
        # with decorators
        orig_socket.connect(self, *args, **kwargs)

socket.socket = LogSocket


def report_on_exit():
    open_report()
    connect_report()

atexit.register(report_on_exit)
