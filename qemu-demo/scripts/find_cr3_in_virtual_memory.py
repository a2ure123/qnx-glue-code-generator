#!/usr/bin/env python3
from qemu.qmp import QMPClient
import asyncio
import re
from argparse import ArgumentParser

debug = False


async def find_cr3(addr):
    """
    Find the virtual address of CR3 register through QEMU monitor.
    """

    qmp = QMPClient("")
    await qmp.connect(addr)

    regs = await qmp.execute(
        "human-monitor-command", {"command-line": "info registers"}
    )
    cr3 = re.search(r"CR3=([0-9a-fA-F]+)", str(regs)).group(1)
    # from hex to int
    cr3 = int(cr3, 16)
    if debug:
        print(regs)

    print(f"[x] CR3={hex(cr3)}")

    mem = await qmp.execute("human-monitor-command", {"command-line": "info mem"})
    # format: 0000000008045000-0000000008048000 0000000000003000 urw
    # parse it
    for line in str(mem).split("\n"):
        if not line:
            continue
        mem, size, perm = line.split(" ")
        start, end = mem.split("-")
        start = int(start, 16)
        end = int(end, 16)
        size = int(size, 16)
        pa = await qmp.execute(
            "human-monitor-command",
            {"command-line": f"gva2gpa {hex(start)}"},
        )
        pa = int(str(pa).split(" ")[1], 16)
        if debug:
            print(
                f"[-] start={hex(start)} end={hex(end)} size={hex(size)} pa={hex(pa)} pa_end={hex(pa+size)} perm={perm.strip()}"
            )

        if pa <= cr3 <= pa + size:
            print(f"CR3={hex(cr3)} is in {hex(start)}-{hex(end)}")
            break
    else:
        print(f"CR3={hex(cr3)} is not in any memory region")


if __name__ == "__main__":
    parser = ArgumentParser(description=find_cr3.__doc__)
    parser.add_argument(
        "-d", "--debug", action="store_true", help="debug mode", default=False
    )
    parser.add_argument(
        "-H",
        "--host",
        help="QEMU monitor host, default: 127.0.0.1",
        default="127.0.0.1",
    )
    parser.add_argument(
        "-p", "--port", help="QEMU monitor port, default: 4444", default=4444, type=int
    )
    args = parser.parse_args()

    debug = args.debug

    asyncio.run(find_cr3((args.host, args.port)))
