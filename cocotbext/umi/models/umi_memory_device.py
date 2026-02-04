from cocotbext.umi.sumi import SumiCmd, SumiCmdType, SumiTransaction
from cocotbext.umi.tumi import TumiTransaction
from cocotbext.umi.drivers.sumi_driver import SumiDriver
from cocotbext.umi.monitors.sumi_monitor import SumiMonitor


class UmiMemoryDevice:
    """
    Virtual memory device that responds to UMI read/write requests.

    Uses a SumiMonitor to receive requests and a SumiDriver to send responses.
    """

    def __init__(
        self,
        monitor: SumiMonitor,
        driver: SumiDriver,
        log=None
    ):
        self.monitor = monitor
        self.driver = driver
        self.log = log
        self.memory: dict[int, int] = {}

        self.dw = self.driver.get_bus_width()
        self.aw = self.driver.get_addr_width()

        self.monitor.add_callback(self._on_transaction)

    def _on_transaction(self, transaction: SumiTransaction):
        """Callback invoked when the monitor receives a transaction."""
        cmd_type = int(transaction.cmd.cmd_type)

        if cmd_type == SumiCmdType.UMI_REQ_WRITE:
            self._handle_write(transaction, send_response=True)
        elif cmd_type == SumiCmdType.UMI_REQ_POSTED:
            self._handle_write(transaction, send_response=False)
        elif cmd_type == SumiCmdType.UMI_REQ_READ:
            self._handle_read(transaction)
        else:
            if self.log:
                self.log.warning(f"Unhandled UMI command type: 0x{cmd_type:02x}")

    def _handle_write(self, transaction: SumiTransaction, send_response: bool = True):
        """Handle a write request by storing data and optionally sending response."""
        dstaddr = int(transaction.da)
        data = transaction.data
        size = int(transaction.cmd.size)
        length = int(transaction.cmd.len)
        data_size = (length + 1) << size

        if self.log:
            self.log.info(
                f"MEM WRITE: addr=0x{dstaddr:08x} size={data_size} "
                f"data={data[:data_size].hex()}"
            )

        for i in range(data_size):
            self.memory[dstaddr + i] = data[i]

        if send_response:
            resp_cmd = SumiCmd.from_fields(
                cmd_type=SumiCmdType.UMI_RESP_WRITE,
                size=0,
                len=0,
                eom=1
            )
            resp = SumiTransaction(
                cmd=resp_cmd,
                da=int(transaction.sa),
                sa=int(transaction.da),
                data=bytes([0]),
                addr_width=transaction._addr_width
            )
            self.driver.append(resp)

    def _handle_read(self, transaction: SumiTransaction):
        """Handle a read request by returning data from memory."""
        srcaddr = int(transaction.da)
        size = int(transaction.cmd.size)
        length = int(transaction.cmd.len)
        data_size = (length + 1) << size

        data = bytes(self.memory.get(srcaddr + i, 0) for i in range(data_size))

        if self.log:
            self.log.info(
                f"MEM READ: addr=0x{srcaddr:08x} size={data_size} "
                f"data={data.hex()}"
            )

        resp_cmd = SumiCmd.from_fields(
            cmd_type=SumiCmdType.UMI_RESP_READ,
            size=size,
            len=length,
            eom=1
        )

        tumi_trans = TumiTransaction(
            cmd=resp_cmd,
            da=int(transaction.sa),
            sa=int(transaction.da),
            data=data
        )
        for sumi_trans in tumi_trans.to_sumi(data_bus_size=self.dw//8, addr_width=self.aw):
            self.driver.append(sumi_trans)

    def read(self, address: int, length: int = 1) -> bytes:
        """Read bytes from virtual memory directly."""
        return bytes(self.memory.get(address + i, 0) for i in range(length))

    def write(self, address: int, data: bytes):
        """Write bytes to virtual memory directly (for test setup)."""
        for i, byte in enumerate(data):
            self.memory[address + i] = byte

    def dump_memory(self) -> list[tuple[int, int]]:
        """Return a sorted list of (address, value) tuples."""
        return sorted(self.memory.items())

    def clear(self):
        """Clear all memory contents."""
        self.memory.clear()
