#!/usr/bin/env python
# In-source entry to start lumina for debug puporses.
# Will not be installed with pip install
import sys
import os
sys.path.insert(0,os.path.relpath(os.path.join(os.path.join(os.path.dirname(__file__),'..'))))
import lumina.main
lumina.main.main(sys.argv)
