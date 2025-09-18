# Generate a test image


## Usage

1. run `init-fs.sh` to build a debian rootfs
2. run `build.sh` to build binaries for fuzzing

NOTE: Before running following command, you are supposed 
to mount dev and proc filesystems to the rootfs by running
`mount-dev.sh mount`

And then, you can run following:

- The `run.sh` is script to run fuzz-test program.
- The `shell.sh` is script to enter the fuzz environment.
