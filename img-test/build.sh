#!/bin/bash
#
DIST=dist

I_LOCAL_BIN=/opt/qol/bin
I_LOCAL_LIB=/opt/qol/lib

LOCAL_BIN=${DIST}${I_LOCAL_BIN}
LOCAL_LIB=${DIST}${I_LOCAL_LIB}

if [ -z "$QNX_TARGET" ]; then
	echo "QNX_TARGET is not set"
	exit 1
fi

patch_qnx_bin() {
	PROG=$1
	if file "$PROG" | grep -q "interpreter"; then
		sudo chmod +x "$PROG"
		sudo patchelf --set-interpreter ${I_LOCAL_LIB}/libc.so $PROG
	fi
	sudo patchelf --replace-needed libc.so.4 ${I_LOCAL_LIB}/libc.so $PROG
	sudo patchelf --add-rpath ${I_LOCAL_LIB} $PROG
}

copy_and_patch() {
	PROG=$1
	DEST=$2

	sudo cp "$PROG" "$DEST"
	patch_qnx_bin ${DEST}/$(basename "$PROG")
}

copy_bin() {
	PROG=$1
	copy_and_patch $PROG $LOCAL_BIN
}

copy_lib() {
	LIB=$1
	copy_and_patch $LIB $LOCAL_LIB
}

sudo mkdir -p $DIST/etc/system/config $LOCAL_BIN $LOCAL_LIB
sudo cp ../qol/musl/lib/libc.so $LOCAL_LIB

# build test bin  ^^^^^^
ntox86_64-gcc -g3 -O0 -o fuzz-test test.c -limg
copy_bin fuzz-test
rm fuzz-test
# build test bin  $$$$$$

copy_lib ${QNX_TARGET}/x86_64/lib/libimg.so.1
copy_lib ${QNX_TARGET}/x86_64/usr/lib/libtiff.so.5
copy_lib ${QNX_TARGET}/x86_64/usr/lib/libpng16.so.0
copy_lib ${QNX_TARGET}/x86_64/lib/libjpeg.so.4
copy_lib ${QNX_TARGET}/x86_64/usr/lib/libgif.so.5
copy_lib ${QNX_TARGET}/x86_64/usr/lib/libz.so.2
copy_lib ${QNX_TARGET}/x86_64/usr/lib/liblzma.so.5
copy_lib ${QNX_TARGET}/x86_64/lib/libm.so.3

sudo cp ${QNX_TARGET}/etc/system/config/img.conf $DIST/etc/system/config
for lib in ${QNX_TARGET}/x86_64/lib/dll/img_codec_*.so; do
	copy_lib $lib
done

sudo cp -r cases $DIST/root

cat <<EOF | sudo tee $DIST/root/env.sh > /dev/null
export PATH=${I_LOCAL_BIN}:\$PATH
EOF

