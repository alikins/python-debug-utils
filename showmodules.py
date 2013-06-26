#!/usr/bin/python

import sys
import modulefinder

mf = modulefinder.ModuleFinder()

for filename in sys.argv[1:]:
    mf.run_script(filename)

    for module in mf.modules:
        print module

