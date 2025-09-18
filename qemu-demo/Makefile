.PHONY: start clean image disk

BUILD=system

disk: ./output/ifs.img
	@echo disk done

image: ./output/system.ifs
	@echo image done

start: image
	./scripts/start-qemu.sh

SSH_FILES = $(wildcard ./ssh/*)

output/system.ifs: ./build/$(BUILD).build ./scripts/build.sh $(SSH_FILES)
	./scripts/build.sh $<

output/ifs.img: ./build/fs.build ./output/system.ifs
	./scripts/build-disk.sh

clean:
	rm -rf ./output

