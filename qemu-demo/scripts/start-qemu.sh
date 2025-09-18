#!/bin/bash

DIR=$(realpath ${BASH_SOURCE%/*}/..)

cd $DIR

port=$(($RANDOM % 30000 + 30000))

echo $port >.port

qemu-system-x86_64 \
	-m 4G \
	-kernel ./output/system.ifs \
	-nic user,model=e1000,hostfwd=tcp::$port-:22,hostfwd=tcp::6666-:6666 \
	-s -nographic \
	$*

rm .port

# -d exec,nochain -D /tmp/qemu-log \
# -rtc clock=vm -icount shift=1,align=off \
