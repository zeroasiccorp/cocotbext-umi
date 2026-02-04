# cocotbext-umi

**Cocotb Extensions for UMI (Universal Memory Interface) Verification**

[![Lint](https://github.com/zeroasiccorp/cocotbext-umi/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/zeroasiccorp/cocotbext-umi/actions/workflows/lint.yml)
[![Wheels](https://github.com/zeroasiccorp/cocotbext-umi/actions/workflows/wheels.yml/badge.svg?branch=main)](https://github.com/zeroasiccorp/cocotbext-umi/actions/workflows/wheels.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Overview

cocotbext-umi is a Python library providing [cocotb](https://www.cocotb.org/) extensions for verifying hardware designs that use the [UMI (Universal Memory Interface)](https://github.com/zeroasiccorp/umi) protocol. It includes drivers, monitors, transaction models, and memory simulation components for comprehensive UMI testbench development.

### What is UMI?

[UMI](https://github.com/zeroasiccorp/umi) is a transaction-based standard for accessing memory through request-response message exchange patterns. Key characteristics include:

- **Simple and universal** - A clean, address-based interface that makes everything addressable
- **Layered architecture** - Five abstraction layers (Protocol, Transaction, Signal, Link, Physical)
- **Flexible data handling** - Word sizes up to 1024 bits with up to 256 word transfers per transaction
- **Advanced features** - Atomic operations, QoS support, and protection/security modes
- **Independent channels** - Separate request and response paths for efficient pipelining

## Features

| Feature | Description |
|---------|-------------|
| **SUMI Protocol** | Complete Simple UMI transaction model with all command types |
| **TUMI Support** | Transport UMI for large transaction fragmentation |
| **Cocotb Integration** | Native drivers and monitors for cocotb testbenches |
| **Memory Model** | Virtual memory device for request/response simulation |
| **Bit-level Utilities** | Flexible BitField and BitVector classes for protocol encoding |

## Installation


```bash
git clone https://github.com/zeroasiccorp/cocotbext-umi
cd cocotbext-umi
pip install -e .
```

## Architecture

```
cocotbext-umi/
├── sumi.py              # SUMI protocol: commands, transactions, enums
├── tumi.py              # TUMI: transport-level transaction handling
├── drivers/
│   └── sumi_driver.py   # Cocotb driver for sending UMI transactions
├── monitors/
│   └── sumi_monitor.py  # Cocotb monitor for receiving UMI transactions
├── models/
│   └── umi_memory_device.py  # Virtual memory responder model
└── utils/
    ├── bit_utils.py     # BitField and BitVector utilities
    ├── generators.py    # Transaction generators
    └── vrd_transaction.py  # Valid-ready-data transaction wrapper
```

## Quick Start

### Basic Testbench Setup

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from cocotbext.umi.sumi import SumiCmd, SumiCmdType, SumiTransaction
from cocotbext.umi.drivers.sumi_driver import SumiDriver
from cocotbext.umi.monitors.sumi_monitor import SumiMonitor
from cocotbext.umi.models.umi_memory_device import UmiMemoryDevice

@cocotb.test()
async def test_umi_memory(dut):
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Create driver and monitor
    driver = SumiDriver(dut, "umi_req", dut.clk)
    monitor = SumiMonitor(dut, "umi_resp", dut.clk)

    # Create memory model
    mem = UmiMemoryDevice(monitor, driver, log=dut._log)

    # Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Send a write transaction
    write_cmd = SumiCmd.from_fields(
        cmd_type=SumiCmdType.UMI_REQ_WRITE,
        size=2,  # 4 bytes
        len=0,   # 1 transfer
        eom=1
    )
    write_txn = SumiTransaction(
        cmd=write_cmd,
        da=0x1000,
        sa=0x0,
        data=bytes([0xDE, 0xAD, 0xBE, 0xEF])
    )
    driver.append(write_txn)
```

### Creating UMI Transactions

```python
from cocotbext.umi.sumi import SumiCmd, SumiCmdType, SumiTransaction

# Create a read request
read_cmd = SumiCmd.from_fields(
    cmd_type=SumiCmdType.UMI_REQ_READ,
    size=3,    # 8 bytes per word
    len=3,     # 4 transfers (len+1)
    eom=1      # End of message
)

read_txn = SumiTransaction(
    cmd=read_cmd,
    da=0x2000,      # Destination address
    sa=0x100,       # Source address (for response routing)
    data=None       # No data for read requests
)

# Create a posted write (no response expected)
posted_cmd = SumiCmd.from_fields(
    cmd_type=SumiCmdType.UMI_REQ_POSTED,
    size=0,    # 1 byte
    len=7,     # 8 bytes total
    eom=1
)

posted_txn = SumiTransaction(
    cmd=posted_cmd,
    da=0x3000,
    sa=0x0,
    data=bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
)
```

### Using TUMI for Large Transactions

```python
from cocotbext.umi.tumi import TumiTransaction
from cocotbext.umi.sumi import SumiCmd, SumiCmdType

# Create a large transaction that needs fragmentation
cmd = SumiCmd.from_fields(cmd_type=SumiCmdType.UMI_REQ_WRITE)
large_data = bytes(range(256))  # 256 bytes

tumi_txn = TumiTransaction(
    cmd=cmd,
    da=0x4000,
    sa=0x0,
    data=large_data
)

# Convert to multiple SUMI transactions based on bus width
sumi_transactions = tumi_txn.to_sumi(data_bus_size=32)  # 32-byte bus
for txn in sumi_transactions:
    driver.append(txn)
```

## API Reference

### SUMI Command Types

| Command | Value | Direction | Description |
|---------|-------|-----------|-------------|
| `UMI_REQ_READ` | 0x01 | Request | Read/load request |
| `UMI_REQ_WRITE` | 0x03 | Request | Write/store with acknowledgment |
| `UMI_REQ_POSTED` | 0x05 | Request | Posted write (no response) |
| `UMI_REQ_RDMA` | 0x07 | Request | Remote DMA command |
| `UMI_REQ_ATOMIC` | 0x09 | Request | Atomic read-modify-write |
| `UMI_REQ_ERROR` | 0x0F | Request | Error message |
| `UMI_REQ_LINK` | 0x2F | Request | Link control |
| `UMI_RESP_READ` | 0x02 | Response | Read response with data |
| `UMI_RESP_WRITE` | 0x04 | Response | Write acknowledgment |
| `UMI_RESP_LINK` | 0x0E | Response | Link control response |

### SUMI Command Header (32-bit)

| Bits | Field | Description |
|------|-------|-------------|
| [4:0] | `cmd_type` | Command opcode |
| [7:5] | `size` | Word size (bytes = 2^SIZE) |
| [15:8] | `len` | Transfer count (LEN+1 words) |
| [19:16] | `qos` | Quality of service |
| [21:20] | `prot` | Protection mode |
| [22] | `eom` | End of message |
| [23] | `eof` | End of frame |
| [24] | `ex` | Exclusive access |
| [26:25] | `u` | User bits / error code |
| [31:27] | `hostid` | Host ID |

### Atomic Operation Types

| Type | Value | Description |
|------|-------|-------------|
| `UMI_ATOMIC_ADD` | 0x00 | Atomic add |
| `UMI_ATOMIC_AND` | 0x01 | Atomic AND |
| `UMI_ATOMIC_OR` | 0x02 | Atomic OR |
| `UMI_ATOMIC_XOR` | 0x03 | Atomic XOR |
| `UMI_ATOMIC_MAX` | 0x04 | Atomic signed maximum |
| `UMI_ATOMIC_MIN` | 0x05 | Atomic signed minimum |
| `UMI_ATOMIC_MAXU` | 0x06 | Atomic unsigned maximum |
| `UMI_ATOMIC_MINU` | 0x07 | Atomic unsigned minimum |
| `UMI_ATOMIC_SWAP` | 0x08 | Atomic swap |

### SumiDriver

Cocotb bus driver for sending UMI transactions.

**Signals:**
- `valid` - Transaction valid
- `cmd` - 32-bit command header
- `dstaddr` - Destination address
- `srcaddr` - Source address
- `data` - Data payload
- `ready` - Backpressure from receiver

**Methods:**
- `append(transaction)` - Queue a transaction for sending
- `get_bus_width()` - Get data bus width in bits
- `get_addr_width()` - Get address bus width in bits

### SumiMonitor

Cocotb bus monitor for receiving UMI transactions.

**Signals:** Same as SumiDriver

**Methods:**
- `add_callback(fn)` - Register callback for received transactions
- `get_bus_width()` - Get data bus width in bits
- `get_addr_width()` - Get address bus width in bits

### UmiMemoryDevice

Virtual memory model that responds to UMI read/write requests.

**Methods:**
- `read(address, length)` - Direct memory read
- `write(address, data)` - Direct memory write
- `dump_memory()` - Get all memory contents
- `clear()` - Clear memory

## Dependencies

- [cocotb](https://www.cocotb.org/) >= 2.0.1
- [cocotb-bus](https://github.com/cocotb/cocotb-bus) >= 0.3.0
- [siliconcompiler](https://github.com/siliconcompiler/siliconcompiler) >= 0.35.0
- Python >= 3.10

## Contributing

We welcome contributions! Please see our [GitHub Issues](https://github.com/zeroasiccorp/cocotbext-umi/issues) for tracking requests and bugs.

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

Copyright 2025 Zero ASIC Corporation
