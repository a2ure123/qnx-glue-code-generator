#!/bin/bash
DIR=$(realpath ${BASH_SOURCE%/*}/..)
cd $DIR

[ -z $2 ] && set -- "$1" "./"

scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ./ssh/client.rsa -P $(cat .port) root@127.0.0.1:"$1" "$2"
