#!/usr/bin/python
# -*- coding: utf-8 -*-

from af_sync_single import AFSingle
import datetime, time

instances = []

host = '192.168.50.154'
for service in ['test1', 'test2', 'test3', 'test4']:
    for format in ['mp2', 'mp3']:
        instances.append(
            AFSingle(host=host, service=service,format=format)
        )

host = '192.168.50.155'
for service in ['test5', 'test6', 'test7', 'test8']:
    for format in ['mp2', 'mp3']:
        instances.append(
            AFSingle(host=host, service=service,format=format)
        )

while True:
    next_run_time = datetime.datetime.now() + datetime.timedelta(
        milliseconds=1250)

    for instance in instances:
        instance.step()

    now = datetime.datetime.now()
    if now < next_run_time:
        print 'Sleeping for %f seconds' % (next_run_time - now).total_seconds()
        time.sleep((next_run_time - now).total_seconds())
