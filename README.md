# AutoDiscHostLoad

This file will load in hosts to OP5 configuration using an input file that is pulled from the autodiscovery API endpoint.

Use Case: Poller running in a separate VLAN cannot make changes to master config. Take the json from the Autodiscovery job and use it as input to this script using the OP5 Master as the server.

By default it will prompt for host names, the -n flag will use the address as the host name.

It will add a hostgroup if specified with the -g option. Hostgroup must already exist, there is a validation prior to executing changes.

It will use a template if specified with the -t option. Template must already exist, there is a validation prior to executing changes.

The directLoad version will require both master and poller host addresses. It will reach out to the poller and use the latest autodiscovery execution id and load those hosts (or you can specify an execution id with -x).
