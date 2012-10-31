#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime

date = datetime.datetime.strptime('2013-05-13', '%Y-%m-%d')

if not date:
    x = datetime.datetime.now().strftime('%Y-%m-%d')
else:
    x = date.strftime('%Y-%m-%d')

x = datetime.datetime.now().strftime('%Y-%m-%d') if not date else date.strftime('%Y-%m-%d')

#x = datetime.datetime.now().strftime('%Y-%m-%d') or date.strftime('%Y-%m-%d')

print x
