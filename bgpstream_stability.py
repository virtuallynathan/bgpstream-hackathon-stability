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
import requests
import multiprocessing
from _pybgpstream import BGPStream, BGPRecord, BGPElem
from collections import defaultdict
from netaddr import IPNetwork, IPAddress

with open('hitlist.txt') as f:
    hitlist = f.readlines()



updates = defaultdict(int)

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

updateCount = 0
prefixCount = 0
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
        currCount = updates.get(prefix)
        #prepare the empty list for new date values [successCt,failCt]

        if not currCount:
            currCount = 0
        #if we have a success, increment the succcess counter (0)
        currCount += 1
        updates[prefix] = currCount

        # elem.fields = {'communities': [], 'next-hop': '202.249.2.185', 'prefix': '200.0.251.0/24', 'as-path': '25152 6939 12956 10834'}
        elem = rec.get_next_elem()
	updateCount += 1

probeList = get_ripe_probes(updates)
print json.dumps(probeList, indent=4)


def get_hitlist_ips(prefix_list):
# for each prefix (dict - prefix:count), check if any IP from the hitlist is in the prefix. Return a dict of prefix:list of stable IPs
for line in hitlist:
    #check if anything from the
    if IPAddress("192.168.0.1") in IPNetwork("192.168.0.0/24"):

topN = 10
num = 0

for w in sorted(updates, key=updates.get, reverse=True):
  num += 1
  if num == topN:
      break
  print w, updates[w]

print "Updates: " + str(updateCount)
print "Prefixes: " + str(prefixCount)


def get_ripe_probes(prefix_list):

	def get_probe_list(ip_proto, prefix, return_dict):

		url = "https://atlas.ripe.net/api/v1/probe/?format=json&prefix_%s=%s" %(ip_proto, prefix)
		probe_data = requests.get(url).json()

		probe_count = probe_data["meta"]["total_count"]

		probe_ids = []
		if probe_count > 0:
			for probe in probe_data["objects"]:

				probe_id = probe["id"]
				probe_ids.append(probe_id)

		return_dict[prefix] = {"probe_count": probe_count, "probe_ids": probe_ids}
		return


	jobs = []
	manager = multiprocessing.Manager()
	return_dict = manager.dict()

	for prefix, count in prefix_list.iteritems():
		prefix = prefix.strip()

		if "." in prefix:

			job = multiprocessing.Process(target=get_probe_list, args=("v4", prefix, return_dict))

		elif ":" in prefix:

			job = multiprocessing.Process(target=get_probe_list, args=("v6", prefix, return_dict))

		jobs.append(job)
		job.start()


	for job in jobs:
		job.join()

	#print json.dumps(dict(return_dict), indent=4)
	return dict(return_dict)
