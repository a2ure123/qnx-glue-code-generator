#!/bin/bash

set -e

if [ $# -ne 1 ]; then
	echo "Usage: $0 <program> (program in qnx target path)"
	exit 1
fi

SCRIPT_DIR=${BASH_SOURCE%/*}

DIST=$(realpath ${SCRIPT_DIR}/dist)
SRC=$1
PROG=$DIST/$(basename "$SRC")

MUSL_SO=$(realpath $SCRIPT_DIR/musl/lib/libc.so)

cp "$SRC" $DIST

if file "$PROG" | grep -q "interpreter"; then
	chmod +x "$PROG"
	patchelf --set-interpreter "$MUSL_SO" "$PROG"
fi
patchelf --replace-needed libc.so.4 "$MUSL_SO" "$PROG"
patchelf --add-rpath $DIST "$PROG"
