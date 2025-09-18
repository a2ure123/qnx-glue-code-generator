#!/bin/bash

DIR=$(realpath ${BASH_SOURCE%/*}/..)

cd $DIR

mkdir -p output

FILE=./build/system.build
if [[ -n $1 ]]; then
  FILE=$1
fi


mkifs "$FILE" ./output/system.ifs
