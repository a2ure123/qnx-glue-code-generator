#!/bin/bash

print_help() {
    echo "Usage: $0 [-hd] [--] [fuzz-test options]"
    echo "   -h: print this help message"
    echo "   -d: start gdb"
}

while getopts "hd" opt; do
    case $opt in
    h)
        print_help
        exit 0
        ;;
    d)
        DEBUG=1
        ;;
    \?)
        print_help
        exit 1
        ;;
    esac
done

shift $((OPTIND - 1))

if [ "$1" = "--" ]; then
    shift
fi

if [ -n "$DEBUG" ]; then
    sudo chroot ./dist gdb --args fuzz-test $@
else
    sudo chroot ./dist fuzz-test $@
fi
