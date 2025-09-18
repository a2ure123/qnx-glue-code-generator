#!/bin/bash
DIR=$(realpath ${BASH_SOURCE%/*}/..)
cd $DIR

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ./ssh/client.rsa -p $(cat .port) root@127.0.0.1 "$*"
