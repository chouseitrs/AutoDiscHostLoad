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
required.add_argument("-m", "--master", help="OP5 Server DNS Name or IP. Defaults to localhost", default="localhost", type=str, required=True)
required.add_argument("-p", "--poller", help="OP5 Server DNS Name or IP. Defaults to localhost", default="localhost", type=str, required=True)
optional.add_argument("-x", "--execid", help="Execution ID of the AutoDiscovery job run on the poller", type=str, required=False)
optional.add_argument("-g", "--group", help="hostGroup to be associated with all hosts to be loaded, typically Poller HG, if applicable", type=str, required=False)
optional.add_argument("-t", "--template", help="template to be used with all hosts to be loaded, default is the default-host-template", type=str, required=False)
optional.add_argument("-n", "--noname", help="do not prompt for hostnames", action='store_true')

# Parse the arguments into variables.
args = parser.parse_args()

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

#Create the poller connection
pconn = http.client.HTTPSConnection(
    args.poller,
    context=ssl._create_unverified_context()
)

#Load the JSON from the poller using the execution ID provided via argument
if args.execid:
    pconn.request("GET", "/api/magellan/v1/executions/{execid}/devices".format(execid=args.execid), None, headers)
    pollAD=pconn.getresponse()
    if pollAD.status >= 400:
        print('Template Not Found: Server returned status code {status} - {reason}'.format(status=pollAD.status, reason=pollAD.reason))
        exit(1)
    jsonhostobj = json.loads(pollAD.read())
#Load the most recent completed execution
else:
    pconn.request("GET", "/api/magellan/v1/executions", None, headers)
    pollJobExecs=pconn.getresponse()
    if pollJobExecs.status >= 400:
        print('Template Not Found: Server returned status code {status} - {reason}'.format(status=pollJobExecs.status, reason=pollJobExecs.reason))
        exit(1)
    jsonExecutions = json.loads(pollJobExecs.read())
    if (jsonExecutions[0]["status"] != "completed"):
        print("AutoDiscovery job is currently running or did not finish successfully")
        exit(0)
    execid = jsonExecutions[0]["id"]
    pconn.request("GET", "/api/magellan/v1/executions/{execid}/devices".format(execid=execid), None, headers)
    pollAD=pconn.getresponse()
    if pollAD.status >= 400:
        print('Template Not Found: Server returned status code {status} - {reason}'.format(status=pollAD.status, reason=pollAD.reason))
        exit(1)
    jsonhostobj = json.loads(pollAD.read())


#Push the JSON config up to the master
#Create the master connection
mconn = http.client.HTTPSConnection(
    args.master,
    context=ssl._create_unverified_context()
)

#Verify template and hostgroup exist, if not exit
mconn.request("GET", "/api/config/host_template/{template}".format(template=templ), None, headers)
resT=mconn.getresponse()
if resT.status >= 400:
    print('Template Not Found: Server returned status code {status} - {reason}'.format(status=resTstatus, reason=resT.reason))
    exit(1)

Gveri = {
    'format': 'json',
    'query': "[hostgroups] name=\""+hostgp+"\""
}
mconn.request("GET", "/api/filter/query?{query}".format(query=urlencode(Gveri, quote_via=quote_plus)), None, headers)
resG=mconn.getresponse()
if resG.status >= 400:
    print('HostGroup Not Found: Server returned status code {status} - {reason}'.format(status=resG.status, reason=resG.reason))
    exit(1)

##Parse out discovered addresses and load into a dict, individual upload

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
    mconn.request("POST", "/api/config/host?format=json",urlencode(dict2ld, quote_via=quote_plus), headers)
    res = mconn.getresponse()

mconn.request("POST", "/api/config/change?format=json",'',headers)

