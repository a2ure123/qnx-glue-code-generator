#!/bin/bash

DIR=$(realpath ${BASH_SOURCE%/*}/..)

cd $DIR

mkdir -p output

mkqnx6fsimg ./build/fs.build ./output/ifs.img 
