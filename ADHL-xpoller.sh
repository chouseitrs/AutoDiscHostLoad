#!/bin/bash

usage() { echo "Usage: Run this one on the Poller " 1>&2; exit 1; }


while getopts ":u:m:p:x:" opt; do
  case $opt in
    u) op5user=$OPTARG;;
    m) master=$OPTARG;;
    p) poller=$OPTARG;;  
    x) execid=$OPTARG;; 
    *) usage;;
   esac
done
shift $((OPTIND-1))

if [ -z $op5user ] || [ -z $master ] || [ -z $poller ] || [ -z $execid ]; then
    usage
    exit 1
fi

echo "OP5 API User Password:"
stty_orig=$(stty -g) # save original terminal setting.
stty -echo           # turn-off echoing.
IFS= read -r passwd  # read the password
stty "$stty_orig"    # restore terminal setting.

authstr=$(echo -n $op5user":"$passwd | base64)

# Get the execution id of the latest job execution

curl -k -s --request GET \
  --url https://$poller:443/api/magellan/v1/executions/$execid/devices \
  --header "Authorization: Basic $authstr" \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  &> AutoDiscoveryResults.json

scp AutoDiscoveryResults.json $master:/tmp