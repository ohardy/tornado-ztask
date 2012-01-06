#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding: utf-8
"""
__init__.py

Created by Olivier Hardy on 2011-09-09.
Copyright (c) 2011 Olivier Hardy. All rights reserved.
"""

import os
import sys

__author__      = "Olivier Hardy"
__contact__     = "ohardy@me.com"
__docformat__   = "restructuredtext"

if sys.version_info < (2, 6):
    import warnings
    warnings.warn(DeprecationWarning("""

Python 2.5 support is deprecated and only versions 2.6, 2.7+ is supported


"""))

if not os.environ.get("TORNADO_ZTASK_SETUP", False):
    pass
