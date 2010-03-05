import os, sys
# ../
PATH    = os.path.dirname(__file__)
HOMEDIR = os.path.abspath(os.path.join(PATH, os.path.pardir))
LIBDIR  = os.path.abspath(os.path.join(PATH, 'lib'))
sys.path.append(HOMEDIR)
sys.path.append(LIBDIR)
import unittest_decorator # add @unittest.test decorators and such
sys.modules['unittest'] = sys.modules['unittest_decorator'] # override default unittest module
