#!/usr/bin/env -S ntox86_64-gdb -x

target qnx :6666
set nto-executable /mnt/test
file ./test

set pagination off

tbreak test.c:24
commands
    printf "add symbol files ..."
    set logging file tmp.log
    set logging on
    info meminfo
    set logging off
    shell ./getaddr.sh tmp.log > tmp.input
    source tmp.input
    shell rm tmp.log tmp.input

    source ./poc.gdb
end

run 



