#!/bin/bash
ntox86_64-gcc -o test -O0 -g3 test.c -limg
../qemu-demo/scripts/connect.sh "echo 00 > /mnt/initf"
../qemu-demo/scripts/scp-to.sh ./test
../qemu-demo/scripts/scp-to.sh ~/winwork/poc1

