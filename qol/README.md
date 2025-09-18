# QOL: QNX on Linux

This project is to run QNX binary on linux.
We use modified musl libc to support QNX ABI.

## Usage

1. build patched `musl-libc` first, running `make` in `musl` dir.
2. use `patch.sh` to patch qnx binaries, Usage: `./patch.sh <program>`
    steps in `../img-test/build.sh` may be a reference.

