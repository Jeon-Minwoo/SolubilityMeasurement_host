from enum import Enum
from typing import Callable
import socket
from threading import Thread


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


class RequestHandler:
    BUFFER_SIZE = 1024

    def __init__(self, client: socket.socket, handler: Callable[[ERequest, list], EResponse]):
        self.client = client
        self.handler = handler

        self.__thread = Thread(
            target=RequestHandler.__loop,
            args=(self.client, self.handler))
        self.__thread.start()

    @staticmethod
    def __loop(client: socket.socket, handler: Callable[[ERequest, list], EResponse]):
        while True:
            data = client.recv(RequestHandler.BUFFER_SIZE)

            request = int.from_bytes(data[0:2], byteorder='big')
            request = ERequest.from_value(request)
            args = data[2:]


    def handle(self, request: ERequest, *args) -> EResponse:
        return self.handler(request, *args)
