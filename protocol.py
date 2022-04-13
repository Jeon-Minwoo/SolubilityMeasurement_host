from enum import Enum, EnumMeta
from typing import Callable
import socket
from PyQt6.QtCore import QThread, pyqtSignal


class ByteEnum(Enum):
    def int(self) -> int:
        return int(self.value)

    def bytes(self) -> bytes:
        return bytes([self.int()])

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta):
        data = int(data[0])
        for v in enum:
            if v.int() == data:
                return v
        return None


class ERequest(ByteEnum):
    CAMERA = 0x01
    DISPLAY = 0x02

    CAMERA_TAKE_PICTURE = 0x01 | 0x10
    CAMERA_TOGGLE_TORCH = 0x01 | 0x20

    DISPLAY_TAKE_PICTURE = 0x02 | 0x10
    DISPLAY_SHOW_PICTURE = 0x02 | 0x20

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta = None):
        return ByteEnum.from_bytes(data, ERequest)


class EResponse(ByteEnum):
    OK = 0
    ERROR = 1
    REFUSE = 2

    @staticmethod
    def from_bytes(data: bytes, enum: EnumMeta = None):
        return ByteEnum.from_bytes(data, EResponse)


def resolve_request(data: bytes) -> (ERequest, bytes):
    request = ERequest.from_bytes(data[0:1])
    args = data[1:]
    return request, args


class Interactor(QThread):
    BUFFER_SIZE = 1024
    proc = pyqtSignal(ERequest, bytes, EResponse)

    def __init__(self,
                 client: socket.socket,
                 handler: Callable[[ERequest, bytes], EResponse]):
        super(Interactor, self).__init__()

        self.client = client
        self.handler = handler

    def run(self):
        while True:
            data = self.client.recv(Interactor.BUFFER_SIZE)
            request, args = resolve_request(data)

            response = self.handler(request, args)
            self.client.send(int.to_bytes(response.value, byteorder='big', length=2, signed=False))

            self.proc(request, args, response)

    def request(self, request: ERequest, args: bytes):
        data = b''.join([request.bytes(), args])
        self.client.send(data)
