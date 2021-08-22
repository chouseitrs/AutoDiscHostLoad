#!/usr/bin/python3


import http.client
import json
from urllib.parse import urlencode, quote_plus
from getpass import getpass
import base64
import ssl
import argparse
import os
from array import array


# Create the command line argument parser
parser = argparse.ArgumentParser(description="OP5 API Add Hosts Bulk")

# Add the groups for the required and optional command line arguments. Also hide the default grouping
parser._action_groups.pop()
required = parser.add_argument_group('Required Arguments')
optional = parser.add_argument_group('Modifier Arguments')

# Add the command line arguments
required.add_argument("-u", "--username", help="OP5 API username", type=str, required=True)
required.add_argument("-f", "--file", help="Path to json file output from AutoDisc with hosts to load", type=str, required=True)
required.add_argument("-s", "--server", help="OP5 Server DNS Name or IP. Defaults to localhost", default="localhost", type=str, required=True)
optional.add_argument("-g", "--group", help="hostGroup to be associated with all hosts to be loaded, typically Poller HG, if applicable", type=str, required=False)
optional.add_argument("-t", "--template", help="template to be used with all hosts to be loaded, default is the default-host-template", type=str, required=False)
optional.add_argument("-n", "--noname", help="do not prompt for hostnames", action='store_true')

# Parse the arguments into variables.
args = parser.parse_args()

conn = http.client.HTTPSConnection(
    args.server,
    context=ssl._create_unverified_context()
)
if args.noname:
    skipnaming=True
else:
    skipnaming=False

if args.group:
    hostgp=args.group   
else:
    hostgp=""

if args.template:
    templ=args.template   
else:
    templ="default-host-template"

# Get the password input from user
apipw=getpass("OP5 API Password:")


# Create the headers to allow authentication and return encoding.
headers = {
    'accept': "application/json",
    'Authorization': 'Basic {auth_string}'.format(auth_string=base64.b64encode(str.encode('{username}:{password}'.format(username=args.username, password=apipw))).decode('utf=8'))
}

##Verify template and hostgroup exist, if not exit

conn.request("GET", "/api/config/host_template/{template}".format(template=templ), None, headers)
resT=conn.getresponse()
if resT.status >= 400:
    print('Template Not Found: Server returned status code {status} - {reason}'.format(status=resTstatus, reason=resT.reason))
    exit(1)

Gveri = {
    'format': 'json',
    'query': "[hostgroups] name=\""+hostgp+"\""
}
conn.request("GET", "/api/filter/query?{query}".format(query=urlencode(Gveri, quote_via=quote_plus)), None, headers)
resG=conn.getresponse()
if resG.status >= 400:
    print('HostGroup Not Found: Server returned status code {status} - {reason}'.format(status=resG.status, reason=resG.reason))
    exit(1)

##Parse out discovered addresses and load into a dict, individual upload

with open(args.file) as hostsfile:
    jsonhostobj=json.load(hostsfile)

dict2ld={}
for add in range(len(jsonhostobj)):
    print("Creating Host for: "+str(jsonhostobj[add]["address"]))
    if skipnaming:
        host_name=jsonhostobj[add]["address"]
    else:
        host_name=input("Please enter a name for the Host: ")
    dict2ld={
        "host_name":host_name,
        "address":jsonhostobj[add]["address"],
        "template":templ,
        "hostgroups":hostgp
    }
    conn.request("POST", "/api/config/host?format=json",urlencode(dict2ld, quote_via=quote_plus), headers)
    res = conn.getresponse()

conn.request("POST", "/api/config/change?format=json",'',headers)

