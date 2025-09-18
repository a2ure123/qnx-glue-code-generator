#!/bin/bash
#
set -e

if [ $(id -u) -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

DIST=dist

debootstrap --variant=minbase \
    --components=main,restricted,universe,multiverse \
    jammy $DIST http://mirrors.hust.edu.cn/ubuntu

cp /etc/resolv.conf ${DIST}/etc/resolv.conf

trap "./mount-dev.sh umount" EXIT
./mount-dev.sh mount

chroot ${DIST} bash -c 'apt-get update \
    && apt-get install -y gdb vim-tiny build-essential \
        git wget curl python3-dev python3-pip python3-setuptools \
        automake autoconf bison flex ninja-build libglib2.0-dev cmake cargo'

chroot ${DIST} bash -c 'cd root && git clone https://github.com/AFLplusplus/AFLplusplus \
    && cd AFLplusplus \
    && make NO_NYX=1 binary-only && make install'

#     && RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static \
#       RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup \
#       curl -sSf https://mirrors.ustc.edu.cn/misc/rustup-install.sh | sh -s -- -y \
#    && source $HOME/.cargo/env \
