#!/bin/bash
DIR=$(realpath ${BASH_SOURCE%/*}/..)

[ -z $1 ] && set -- "$1" "/mnt/"

scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ${DIR}/ssh/client.rsa -P $(cat ${DIR}/.port) "$1" root@127.0.0.1:"$2"
