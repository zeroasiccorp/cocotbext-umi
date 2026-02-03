from enum import IntEnum
from typing import Optional
import dataclasses
import copy

from cocotbext.umi.utils.bit_utils import BitField, BitVector
from cocotbext.umi.utils.vrd_transaction import VRDTransaction


class SumiCmdType(IntEnum):
    """UMI Command Opcodes (CMD[4:0])"""
    # Invalid transaction indicator
    UMI_INVALID = 0x00

    # Requests (host -> device)
    UMI_REQ_READ = 0x01       # read/load
    UMI_REQ_WRITE = 0x03      # write/store with ack
    UMI_REQ_POSTED = 0x05     # posted write (no response)
    UMI_REQ_RDMA = 0x07       # remote DMA command
    UMI_REQ_ATOMIC = 0x09     # atomic read-modify-write
    UMI_REQ_USER0 = 0x0B      # reserved for user
    UMI_REQ_FUTURE0 = 0x0D    # reserved for future use
    UMI_REQ_ERROR = 0x0F      # error message (SIZE=0x0)
    UMI_REQ_LINK = 0x2F       # link ctrl (SIZE=0x1)

    # Responses (device -> host)
    UMI_RESP_READ = 0x02      # response to read request (with data)
    UMI_RESP_WRITE = 0x04     # response (ack) from write request
    UMI_RESP_USER0 = 0x06     # reserved for user (no data)
    UMI_RESP_USER1 = 0x08     # reserved for user (with data)
    UMI_RESP_FUTURE0 = 0x0A   # reserved for future use (no data)
    UMI_RESP_FUTURE1 = 0x0C   # reserved for future use (with data)
    UMI_RESP_LINK = 0x0E      # link ctrl response (SIZE=0x0)

    @classmethod
    def supports_streaming(cls, value):
        """Check if the command type supports streaming (multiple data transfers)."""
        return value in [
            SumiCmdType.UMI_REQ_WRITE,
            SumiCmdType.UMI_REQ_POSTED,
            SumiCmdType.UMI_RESP_READ
        ]

    @classmethod
    def is_request(cls, value):
        """Check if the command is a request (host -> device)."""
        return value in [
            SumiCmdType.UMI_REQ_READ,
            SumiCmdType.UMI_REQ_WRITE,
            SumiCmdType.UMI_REQ_POSTED,
            SumiCmdType.UMI_REQ_RDMA,
            SumiCmdType.UMI_REQ_ATOMIC,
            SumiCmdType.UMI_REQ_USER0,
            SumiCmdType.UMI_REQ_FUTURE0,
            SumiCmdType.UMI_REQ_ERROR,
            SumiCmdType.UMI_REQ_LINK,
        ]

    @classmethod
    def is_response(cls, value):
        """Check if the command is a response (device -> host)."""
        return value in [
            SumiCmdType.UMI_RESP_READ,
            SumiCmdType.UMI_RESP_WRITE,
            SumiCmdType.UMI_RESP_USER0,
            SumiCmdType.UMI_RESP_USER1,
            SumiCmdType.UMI_RESP_FUTURE0,
            SumiCmdType.UMI_RESP_FUTURE1,
            SumiCmdType.UMI_RESP_LINK,
        ]

    @classmethod
    def has_data(cls, value):
        """Check if the command type carries data."""
        return value in [
            SumiCmdType.UMI_REQ_WRITE,
            SumiCmdType.UMI_REQ_POSTED,
            SumiCmdType.UMI_REQ_ATOMIC,
            SumiCmdType.UMI_REQ_USER0,
            SumiCmdType.UMI_REQ_FUTURE0,
            SumiCmdType.UMI_RESP_READ,
            SumiCmdType.UMI_RESP_USER1,
            SumiCmdType.UMI_RESP_FUTURE1,
        ]

    @classmethod
    def has_source_addr(cls, value):
        """Check if the command type includes source address (SA)."""
        return value in [
            SumiCmdType.UMI_REQ_READ,
            SumiCmdType.UMI_REQ_WRITE,
            SumiCmdType.UMI_REQ_POSTED,
            SumiCmdType.UMI_REQ_RDMA,
            SumiCmdType.UMI_REQ_ATOMIC,
            SumiCmdType.UMI_REQ_USER0,
            SumiCmdType.UMI_REQ_FUTURE0,
            SumiCmdType.UMI_REQ_ERROR,
        ]


class SumiAtomicType(IntEnum):
    """Atomic Transaction Types (ATYPE[7:0]) - used in LEN field for REQ_ATOMIC"""
    UMI_ATOMIC_ADD = 0x00
    UMI_ATOMIC_AND = 0x01
    UMI_ATOMIC_OR = 0x02
    UMI_ATOMIC_XOR = 0x03
    UMI_ATOMIC_MAX = 0x04
    UMI_ATOMIC_MIN = 0x05
    UMI_ATOMIC_MAXU = 0x06
    UMI_ATOMIC_MINU = 0x07
    UMI_ATOMIC_SWAP = 0x08


class SumiErrorCode(IntEnum):
    """Error Codes (ERR[1:0]) - used in U field for responses"""
    UMI_ERR_OK = 0b00       # OK (no error)
    UMI_ERR_EXOK = 0b01     # Successful exclusive access
    UMI_ERR_DEVERR = 0b10   # Device error
    UMI_ERR_NETERR = 0b11   # Network error


class SumiProtMode(IntEnum):
    """Protection Mode (PROT[1:0])"""
    UMI_PROT_UNPRIVILEGED_SECURE = 0b00
    UMI_PROT_PRIVILEGED_SECURE = 0b01
    UMI_PROT_UNPRIVILEGED_NONSECURE = 0b10
    UMI_PROT_PRIVILEGED_NONSECURE = 0b11


class SumiSize(IntEnum):
    """Transaction Word Size (SIZE[2:0]) - bytes per word = 2^SIZE"""
    UMI_SIZE_1 = 0b000    # 1 byte
    UMI_SIZE_2 = 0b001    # 2 bytes
    UMI_SIZE_4 = 0b010    # 4 bytes
    UMI_SIZE_8 = 0b011    # 8 bytes
    UMI_SIZE_16 = 0b100   # 16 bytes
    UMI_SIZE_32 = 0b101   # 32 bytes
    UMI_SIZE_64 = 0b110   # 64 bytes
    UMI_SIZE_128 = 0b111  # 128 bytes

    def bytes_per_word(self) -> int:
        """Return the number of bytes per word for this SIZE value."""
        return 1 << self.value


@dataclasses.dataclass
class SumiCmd(BitVector):
    """
    UMI Command Header (32 bits)

    Bit layout:
        [4:0]   - opcode (cmd_type): Command opcode
        [7:5]   - size: Word size (bytes = 2^SIZE)
        [15:8]  - len: Word transfers per message (transfers = LEN+1)
                  For REQ_ATOMIC, this field is ATYPE (atomic operation type)
        [19:16] - qos: Quality of service
        [21:20] - prot: Protection mode
        [22]    - eom: End of message indicator
        [23]    - eof: End of frame indicator
        [24]    - ex: Exclusive access indicator
        [26:25] - u: User bits (for requests) or ERR (for responses)
        [31:27] - hostid: Host ID
    """

    # Bits [4:0] - Command opcode
    cmd_type: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=5, offset=0)
    )

    # Bits [7:5] - Word size (bytes per word = 2^SIZE)
    size: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=3, offset=5)
    )

    # Bits [15:8] - Transfer count (LEN+1 words) or ATYPE for atomics
    len: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=8, offset=8)
    )

    # Bits [19:16] - Quality of service
    qos: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=4, offset=16)
    )

    # Bits [21:20] - Protection mode
    prot: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=2, offset=20)
    )

    # Bit [22] - End of message
    eom: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=1, offset=22)
    )

    # Bit [23] - End of frame
    eof: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=1, offset=23)
    )

    # Bit [24] - Exclusive access
    ex: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=1, offset=24)
    )

    # Bits [26:25] - User bits (requests) or error code (responses)
    u: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=2, offset=25)
    )

    # Bits [31:27] - Host ID
    hostid: BitField = dataclasses.field(
        default_factory=lambda: BitField(value=0, width=5, offset=27)
    )

    @property
    def opcode(self) -> int:
        """Alias for cmd_type field."""
        return int(self.cmd_type)

    @property
    def atype(self) -> int:
        """Get ATYPE field (alias for len, used in atomic operations)."""
        return int(self.len)

    @atype.setter
    def atype(self, value: int):
        """Set ATYPE field (alias for len, used in atomic operations)."""
        self.len.from_int(value)

    @property
    def err(self) -> int:
        """Get ERR field (alias for u, used in responses)."""
        return int(self.u)

    @err.setter
    def err(self, value: int):
        """Set ERR field (alias for u, used in responses)."""
        self.u.from_int(value)

    def bytes_per_word(self) -> int:
        """Return the number of bytes per word based on SIZE field."""
        return 1 << int(self.size)

    def transfer_count(self) -> int:
        """Return the number of word transfers (LEN+1)."""
        return int(self.len) + 1

    def total_bytes(self) -> int:
        """Return the total number of bytes in the transaction."""
        return self.bytes_per_word() * self.transfer_count()

    def is_request(self) -> bool:
        """Check if this command is a request."""
        return SumiCmdType.is_request(int(self.cmd_type))

    def is_response(self) -> bool:
        """Check if this command is a response."""
        return SumiCmdType.is_response(int(self.cmd_type))

    def has_data(self) -> bool:
        """Check if this command carries data."""
        return SumiCmdType.has_data(int(self.cmd_type))

    def has_source_addr(self) -> bool:
        """Check if this command includes source address."""
        return SumiCmdType.has_source_addr(int(self.cmd_type))

    def __repr__(self):
        return f"SumiCmd({super().__repr__()})"


class SumiTransaction:

    def __init__(
        self,
        cmd: SumiCmd,
        da: Optional[int],
        sa: Optional[int],
        data: Optional[bytes],
        addr_width: int = 64
    ):
        self.cmd = copy.deepcopy(cmd)
        self.da = BitField(value=da, width=addr_width, offset=0)
        self.sa = BitField(value=sa, width=addr_width, offset=0)
        self.data = data
        self._addr_width = addr_width

    def header_to_bytes(self) -> bytes:
        return (bytes(self.cmd)
                + int.to_bytes(int(self.da), length=self._addr_width//8, byteorder='little')
                + int.to_bytes(int(self.sa), length=self._addr_width//8, byteorder='little'))

    def to_lumi(self, lumi_size, inc_header=True, override_last=None):
        raw = self.data[:(int(self.cmd.len)+1 << int(self.cmd.size))]
        if inc_header:
            raw = self.header_to_bytes() + raw
        # Break raw into LUMI bus sized chunks
        chunks = [raw[i:i+lumi_size] for i in range(0, len(raw), lumi_size)]
        # Zero pad last chunk
        chunks[-1] = chunks[-1] + bytes([0] * (lumi_size - len(chunks[-1])))
        vrd_transactions = []
        for i, chunk in enumerate(chunks):
            # Set last true for the last chunk
            last = (i == len(chunks)-1)
            # Allow user to override last (useful for simulating streaming mode)
            if last and (override_last is not None):
                last = override_last
            # Convert data to a valid ready transaction type
            vrd_transactions.append(VRDTransaction(
                data=chunk,
                last=last
            ))
        return vrd_transactions

    def trunc_and_pad_zeros(self):
        data_len = ((int(self.cmd.len)+1) << int(self.cmd.size))
        self.data = bytes([0] * (len(self.data) - data_len)) + self.data[:data_len]

    def __eq__(self, other):
        if isinstance(other, SumiTransaction):
            # For all command types CMD's must match
            if int(self.cmd) == int(other.cmd):
                # For RESP_WRITE only compare header fields DA
                if int(self.cmd.cmd_type) == SumiCmdType.UMI_RESP_WRITE:
                    return int(self.da) == int(other.da)
                else:
                    my_pkt = self.header_to_bytes() + self.data
                    other_pkt = other.header_to_bytes() + other.data
                    return my_pkt == other_pkt
            return False
        else:
            return False

    def __repr__(self):
        return f"header = {self.header_to_bytes().hex()} data = {self.data.hex()} {self.cmd}"
