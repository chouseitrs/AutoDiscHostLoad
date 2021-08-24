#!/bin/bash

usage() { echo "Usage: $0" 1>&2; exit 1; }

while getopts ":u:m:p:t:g:" opt; do
  case $opt in
    u) op5user=$OPTARG;;
    m) master=$OPTARG;;   
    p) poller=$OPTARG;;   
    t) templ=$OPTARG;;   
    g) hgroup=$OPTARG;;   
    *) usage;;
   esac
done
shift $((OPTIND-1))

if [ -z $op5user ] || [ -z $master ] || [ -z $poller ]; then
    usage
    exit 1
fi

if [ -z $templ ]; then
    templ="default-host-template"
fi

echo "OP5 API User Password:"
stty_orig=$(stty -g) # save original terminal setting.
stty -echo           # turn-off echoing.
IFS= read -r passwd  # read the password
stty "$stty_orig"    # restore terminal setting.

authstr=$(echo -n $op5user":"$passwd | base64)

# Get the execution id of the latest job execution
execid=$(curl -k -s --request GET \
  --url https://$poller:443/api/magellan/v1/executions/ \
  --header "Authorization: Basic $authstr" \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  &> /dev/stdout  | jq .[0][\"id\"]) 
execid=$(echo $execid | sed 's/\"//g')
curl -k -s --request GET \
  --url https://$poller:443/api/magellan/v1/executions/$execid/devices \
  --header "Authorization: Basic $authstr" \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  &> AutoDiscoveryResults.json
ADiscoveries=$(cat AutoDiscoveryResults.json | jq length)
i=0
while [[ $i -lt $ADiscoveries ]]; do
  echo $'\n'"Working on $(cat AutoDiscoveryResults.json | jq .[$i][\"details\"][\"sysName\"] | sed 's/\"//g'):$(cat AutoDiscoveryResults.json | jq .[$i][\"address\"])"
  if [[ $(cat AutoDiscoveryResults.json | jq .[$i][\"status\"]) == "\"monitored\"" ]]; then
      echo $(cat AutoDiscoveryResults.json | jq .[$i][\"address\"])" is already monitored."
  else
      address=$(cat AutoDiscoveryResults.json | jq .[$i][\"address\"] | sed 's/\"//g')
      hostname=$(cat AutoDiscoveryResults.json | jq .[$i][\"details\"][\"sysName\"] | sed 's/\"//g')
      if [ $hostname = 'null' ]; then
        hostname=$address
      fi
      loadstring="host_name|address|template|hostgroups"$'\n'"$hostname|$address|$templ|$hgroup"
      nhjson=$(jq -Rn '
        ( input  | split("|") ) as $keys |
        ( inputs | split("|") ) as $vals |
        [[$keys, $vals] | transpose[] | {key:.[0],value:.[1]}] | from_entries
        ' <<<"$loadstring")
      echo Adding Host to OP5:
      echo "$nhjson"
      curl -k -s --request POST \
        --url "https://$master:443/api/config/host?format=json" \
        --header 'Accept: application/json' \
        --header "Authorization: Basic $authstr" \
        --header 'Content-Type: application/json' \
        --data   "$nhjson"  &>/dev/null

  fi
  let i=$i+1
  sleep 1
done
rm -f 'AutoDiscoveryResults.json'
svstring="user|export_type"$'\n'"$op5user|user_export"
svjson=$(jq -Rn '
        ( input  | split("|") ) as $keys |
        ( inputs | split("|") ) as $vals |
        [[$keys, $vals] | transpose[] | {key:.[0],value:.[1]}] | from_entries
        ' <<<"$svstring")
curl -k -s --request POST \
        --url "https://$master:443/api/nachos/v1/exports" \
        --header 'Accept: application/json' \
        --header "Authorization: Basic $authstr" \
        --header 'Content-Type: application/json' \
        --data   "$svjson" &>/dev/null
