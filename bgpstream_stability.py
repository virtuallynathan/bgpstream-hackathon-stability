#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of pybgpstream
#
# CAIDA, UC San Diego
# bgpstream-info@caida.org
#
# Copyright (C) 2015 The Regents of the University of California.
# Authors: Alistair King, Chiara Orsini
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

from _pybgpstream import BGPStream, BGPRecord, BGPElem
from collections import defaultdict

updates = defaultdict(lambda : defaultdict(int))
​
# create a new bgpstream instance
stream = BGPStream()

# create a reusable bgprecord instance
rec = BGPRecord()

# configure the stream to retrieve Updates records from the RRC06 collector
stream.add_filter('collector', 'rrc06')
stream.add_filter('record-type', 'updates')

# select the time interval to process:
# Wed Apr 1 00:02:50 UTC 2015 -> Wed Apr 1 00:04:30
stream.add_interval_filter(1454284800,1454285700)

# start the stream
stream.start()

count = 0
# print the stream
while(stream.get_next_record(rec)):
    #print rec.status, rec.project +"."+ rec.collector, rec.time
    elem = rec.get_next_elem()
    while(elem):
        # print "\t", elem.type, elem.peer_address, elem.peer_asn, elem.type, elem.fields
        communities = elem.fields.get("communities", "")
        nextHop = elem.fields.get("next-hop", "")
        prefix = elem.fields.get("prefix", "")
        asPath = elem.fields.get("as-path", "")
        asPathList = asPath.split(' ')
        print "Type: " + elem.type + " Prefix " + prefix + " Path: " + asPath
        # see what we have for that date already
        currCount = f.get(prefix)
        #prepare the empty list for new date values [successCt,failCt]
        empty =  {"A": 0, "W": 0}
        # if the date doesn't have a count, set it to empty
        if not currCount:
            currCount = empty
        #if we have a success, increment the succcess counter (0)
        if status == "A":
            currCount[status] += 1
            f[prefix] = currCount
        #else, we have a failue, increment that counter (1)
        else:
            currCount[status] += 1
            f[prefix] = currCount

        # elem.fields = {'communities': [], 'next-hop': '202.249.2.185', 'prefix': '200.0.251.0/24', 'as-path': '25152 6939 12956 10834'}
        elem = rec.get_next_elem()
	count += 1

print count

for key, value in f.iteritems():
    print "Prefix: " + key + " Announce: " + str(value["A"]) + " Withdrawl: " + str(value["W"])
