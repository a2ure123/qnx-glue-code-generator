#!/bin/bash

if [ $(id -u) -ne 0 ]; then
	echo "Please run as root"
	exit 1
fi

DIST=dist

if [ "$1" = "umount" ]; then
    if ! mount | grep -q ${DIST}/dev; then
        echo "Not mounted"
        exit 0
    fi

    # umount ${DIST}/dev/pts
    umount ${DIST}/dev
    umount ${DIST}/proc
    exit 0

elif [ "$1" = "mount" ]; then
    if mount | grep -q ${DIST}/dev; then
        echo "Already mounted"
        exit 0
    fi

    mount --bind /dev ${DIST}/dev
    # mount --bind /dev/pts ${DIST}/dev/pts
    mount --bind /proc ${DIST}/proc
    exit 0
fi


echo "Usage: $0 [mount|umount]"
