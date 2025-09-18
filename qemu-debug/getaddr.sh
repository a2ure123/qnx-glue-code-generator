#!/bin/bash
PREFIX="$QNX_TARGET/x86_64/lib/dll/"

sed -n "
/^\/proc\/boot\/img_codec_/ {
    s#^/proc/boot/\(.*\)#add-symbol-file ${PREFIX}\1.sym #
    h
    n
    s/.*@ \(0x[0-9a-fA-F]*\).*/\1/
    H
    x
    s/\n/ /
    p
}
" $1
