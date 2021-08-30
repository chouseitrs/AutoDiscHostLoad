#!/bin/bash

usage() { echo "Usage: $0" 1>&2; exit 1; }


while getopts ":u:m:t:g:f:" opt; do
  case $opt in
    u) op5user=$OPTARG;;
    m) master=$OPTARG;;   
    f) tfile=$OPTARG;;
    t) templ=$OPTARG;;   
    g) hgroup=$OPTARG;;   
    *) usage;;
   esac
done
shift $((OPTIND-1))

if [ -z $op5user ] || [ -z $master ] || [ -z $tfile ]; then
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


while read -r rline; do
  hostname=$(echo $rline | awk '{ print $2}')
  address=$(echo $rline | awk '{ print $1}')
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
  sleep 1
done < $tfile
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
