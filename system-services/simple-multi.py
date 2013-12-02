#!/usr/bin/python
# -*- coding: utf-8 -*-

from af_sync_single import AFSingle
import datetime, time

instances = []

instances.append(
    AFSingle(host='192.168.50.155', service='test5', format='mp3')
    )
instances.append(
    AFSingle(host='192.168.50.154', service='test4', format='mp3')
    )
instances.append(
    AFSingle(host='192.168.50.155', service='test5', format='mp2')
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
