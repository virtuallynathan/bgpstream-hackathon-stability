#!/usr/bin/env python
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
#

import json
import copy
import math
import requests
import multiprocessing
from _pybgpstream import BGPStream, BGPRecord, BGPElem
from collections import defaultdict
#from netaddr import IPNetwork, IPAddress
from datetime import datetime
from ripe.atlas.cousteau import (
    Ping,
    Traceroute,
    AtlasSource,
    AtlasCreateRequest
)

def deal_with_time_bucket_junk(prefix, timestamp):

    if prefix not in prefixData:
        newBuckets = copy.deepcopy(buckets)
        prefixData[prefix] = newBuckets

    duration = timestamp - stream_start
    bucket = int(duration / 300)
    # pick correct bucket -> then
    prefixData[prefix][bucket]["count"] += 1


def create_time_buckets(start, end):
    time_step = 300  # 5 multiprocessing
    buckets = []
    for x in xrange(start, end, time_step):
        new_end = x + 300
        window = {"start": x, "end": new_end, "count": 0}
        buckets.append(window)
    return buckets


def get_ripe_probes(prefix_list):

    def get_probe_list(ip_proto, prefix_data, return_dict):

        prefix = prefix_data[0]
        count = prefix_data[1]
        bucket_data = prefix_data[2]
        print prefix

        url = "https://atlas.ripe.net/api/v1/probe/?format=json&prefix_%s=%s" % (ip_proto, prefix)
        print "ajm - 1"
        probe_data = requests.get(url).json()
        print "ajm - 2"

        probe_count = probe_data["meta"]["total_count"]
        print "ajm - 3"
        print url, probe_count

        probe_ids = []
        if probe_count > 0:
            for probe in probe_data["objects"]:
                probe_id = probe["id"]
                probe_ids.append(probe_id)

        return_dict[prefix] = {"count": count, "bucket_data": bucket_data, "probe_count": probe_count, "probe_ids": probe_ids}

    jobs = []
    manager = multiprocessing.Manager()
    return_dict = manager.dict()

    for prefix_data in prefix_list:
        prefix = prefix_data[0]
        if "." in prefix:
            job = multiprocessing.Process(target=get_probe_list, args=("v4", prefix_data, return_dict))

        elif ":" in prefix:
            job = multiprocessing.Process(target=get_probe_list, args=("v6", prefix_data, return_dict))

        jobs.append(job)
        job.start()

    for job in jobs:
        job.join()

    return dict(return_dict)


def create_ripe_measurement(prefix_list):
    measurement_count = 0
    measurement_limit = 10
    ATLAS_API_KEY = "secret"
    for prefix, ip_list in prefix_list.iteritems():
        for ip in ip_list:

            ipAddr = ip
            count = 0
            descr = "Prefix: " + prefix + "Flapped " + str(count) + " times"

            ping = Ping(af=4, target=ipAddr, description=descr)

            traceroute = Traceroute(
                af=4,
                target=ipAddr,
                description=descr,
                protocol="ICMP",
            )

            source = AtlasSource(type="area", value="WW", requested=5)

            atlas_request = AtlasCreateRequest(
                start_time=datetime.utcnow(),
                key=ATLAS_API_KEY,
                measurements=[ping, traceroute],
                sources=[source],
                is_oneoff=True
            )

            (is_success, response) = atlas_request.create()
            measurement_count += 1
            if measurement_count > measurement_limit:
                break


updates = defaultdict(int)
prefixData = {}
# create a new bgpstream instance
stream = BGPStream()

# create a reusable bgprecord instance
rec = BGPRecord()

# configure the stream to retrieve Updates records from the RRC06 collector
stream.add_filter('collector', 'rrc06')
stream.add_filter('record-type', 'updates')

stream_start = 1454284800
stream_end = 1454285700
# select the time interval to process:
# Wed Apr 1 00:02:50 UTC 2015 -> Wed Apr 1 00:04:30
stream.add_interval_filter(stream_start, stream_end)
buckets = create_time_buckets(stream_start, stream_end)

# start the stream
stream.start()

while(stream.get_next_record(rec)):

    elem = rec.get_next_elem()

    while(elem):

        communities = elem.fields.get("communities", "")
        nextHop = elem.fields.get("next-hop", "")
        prefix = elem.fields.get("prefix", "")
        asPath = elem.fields.get("as-path", "")
        asPathList = asPath.split(' ')
        time_stamp = rec.time  # unix epoc timestamp 1427846670

        currCount = updates.get(prefix)
        deal_with_time_bucket_junk(prefix, time_stamp)

        if not currCount:
            currCount = 0

        currCount += 1
        updates[prefix] = currCount

        elem = rec.get_next_elem()



for prefix in list(prefixData):
    for bucket in list(prefixData[prefix]):
        if bucket["count"] < 3:
            prefixData[prefix].remove(bucket)

prefixList = []

for prefix in prefixData:

    index = 0
    max_index = 0
    max_val = 0
    last_val = 0

    for bucket in prefixData[prefix]:

        curr = bucket["count"]
        if curr > last_val:
            max_val = curr

        index += 1
        last_val = curr

    if prefixData[prefix]:
        prefixList.append((prefix, max_val, prefixData[prefix][max_index]))


sortedPrefixList = sorted(prefixList, key=lambda x: (x[1], x[0]))
lastNPrefixList = sortedPrefixList[-20:]

#print json.dumps(lastNPrefixList, indent=4)
print json.dumps(get_ripe_probes(lastNPrefixList), indent=4)

#print json.dumps(ripeProbeList, indent=4)
