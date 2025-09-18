#!/usr/bin/env python3
from qemu.qmp import QMPClient
import asyncio
import re
from argparse import ArgumentParser

debug = False


def calculate_page_table_entry(virtual_address):
    # 页表相关参数
    page_size = 4096  # 页大小
    page_table_size = 1 << 9  # 页表项数目
    page_offset_bits = 12  # 页内偏移位数
    level_1_bits = 9  # 一级页表位数
    level_2_bits = 9  # 二级页表位数
    level_3_bits = 9  # 三级页表位数

    # 计算页表索引
    level_1_index = (virtual_address >> page_offset_bits) & (page_table_size - 1)
    level_2_index = (virtual_address >> (page_offset_bits + level_1_bits)) & (
        page_table_size - 1
    )
    level_3_index = (
        virtual_address >> (page_offset_bits + level_1_bits + level_2_bits)
    ) & (page_table_size - 1)
    level_4_index = (
        virtual_address
        >> (page_offset_bits + level_1_bits + level_2_bits + level_3_bits)
    ) & (page_table_size - 1)

    return (
        level_4_index << 3,
        level_3_index << 3,
        level_2_index << 3,
        level_1_index << 3,
    )


def get_data(resp: str):
    d = resp.split(":")[1].strip()
    d = int(d, 16)
    return d, d & 0xFFFFFFFFFF000, (d & 0x8000000000000000) >> 63


async def find_cr3(addr, start, end):
    """
    Find the virtual address of CR3 register through QEMU monitor.
    """

    qmp = QMPClient("")
    await qmp.connect(addr)

    # Get the virtual address of CR3 register
    regs = await qmp.execute(
        "human-monitor-command", {"command-line": "info registers"}
    )
    cr3 = re.search(r"CR3=([0-9a-fA-F]+)", str(regs)).group(1)
    # from hex to int
    cr3 = int(cr3, 16)
    print("CR3: 0x{:x}".format(cr3))

    for addr in range(start, end, 0x1000):
        print("Virtual Address: 0x{:x}".format(addr), end=" | ")
        i4, i3, i2, i1 = calculate_page_table_entry(addr)

        # print("i4: 0x{:x}".format(i4), end=" ")
        # print("i3: 0x{:x}".format(i3), end=" ")
        # print("i2: 0x{:x}".format(i2), end=" ")
        # print("i1: 0x{:x}".format(i1))

        # Get 4-level page table
        pte4 = await qmp.execute(
            "human-monitor-command",
            {"command-line": "xp/1gx 0x{:x}".format(cr3 + i4)},
        )
        pte4, pte4_a, pte4_nx = get_data(str(pte4))

        # Get 3-level page table
        pte3 = await qmp.execute(
            "human-monitor-command",
            {"command-line": "xp/1gx 0x{:x}".format(pte4_a + i3)},
        )
        pte3, pte3_a, pte3_nx = get_data(str(pte3))

        # Get 2-level page table
        pte2 = await qmp.execute(
            "human-monitor-command",
            {"command-line": "xp/1gx 0x{:x}".format(pte3_a + i2)},
        )
        pte2, pte2_a, pte2_nx = get_data(str(pte2))

        # Get 1-level page table
        pte1 = await qmp.execute(
            "human-monitor-command",
            {"command-line": "xp/1gx 0x{:x}".format(pte2_a + i1)},
        )
        pte1, pte1_a, pte1_nx = get_data(str(pte1))

        print("PTE4: 0x{:x} NX: {:x}".format(pte4, pte4_nx), end=" | ")
        print("PTE3: 0x{:x} NX: {:x}".format(pte3, pte3_nx), end=" | ")
        print("PTE2: 0x{:x} NX: {:x}".format(pte2, pte2_nx), end=" | ")
        print("PTE1: 0x{:x} NX: {:x}".format(pte1, pte1_nx))


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

    asyncio.run(
        find_cr3((args.host, args.port), 0xFFFF800006589000, 0xFFFF800006789000)
    )
