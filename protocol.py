from enum import Enum
from typing import Callable
import socket
from PyQt6.QtCore import QThread, pyqtSignal


class ERequest(Enum):
    CAMERA = 0x01
    DISPLAY = 0x02

    CAMERA_TAKE_PICTURE = 0x01 | 0x10
    CAMERA_TOGGLE_TORCH = 0x01 | 0x20

    DISPLAY_TAKE_PICTURE = 0x02 | 0x10
    DISPLAY_SHOW_PICTURE = 0x02 | 0x20

    def short(self):
        return self.value

    @staticmethod
    def from_value(value):
        for v in ERequest:
            if v.short() == value:
                return v
        return None


class EResponse(Enum):
    OK = 0
    ERROR = 1
    REFUSE = 2

    def short(self):
        return self.value

    @staticmethod
    def from_value(value):
        for v in EResponse:
            if v.short() == value:
                return v
        return None


def resolve_request(data: bytes) -> (ERequest, bytes):
    request = int.from_bytes(data[0:2], byteorder='big', signed=False)
    request = ERequest.from_value(request)
    args = data[2:]
    return request, args


class RequestHandler(QThread):
    BUFFER_SIZE = 1024
    proc = pyqtSignal(ERequest, bytes, EResponse)

    def __init__(self,
                 client: socket.socket,
                 handler: Callable[[ERequest, bytes], EResponse]):
        super(RequestHandler, self).__init__()

        self.client = client
        self.handler = handler

    def run(self):
        while True:
            data = self.client.recv(RequestHandler.BUFFER_SIZE)
            request, args = resolve_request(data)

            response = self.handler(request, args)
            self.client.send(int.to_bytes(response.value, byteorder='big', length=2, signed=False))

            self.proc(request, args, response)
