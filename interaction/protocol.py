from byte_enum import ERequest, EResponse
from bundle import Bundle
from typing import Callable
import socket
from PyQt6.QtCore import QThread, pyqtSignal


    return request, args


class Interactor(QThread):
    """
    BUFFER_SIZE = 1024
    proc = pyqtSignal(ERequest, bytes, EResponse)
    received_signal = pyqtSignal(int, EResponse, bytes)

    def __init__(self,
                 client: socket.socket,
                 handler: Callable[[ERequest, bytes], EResponse]):
        super(Interactor, self).__init__()

        self.client = client
        self.handler = handler

    def run(self) -> None:
        """
        Main routine for this thread.
        :return: None
        while True:
            data = self.client.recv(Interactor.BUFFER_SIZE)
            request, args = resolve_request(data)

            self.client.send(int.to_bytes(response.value, byteorder='big', length=2, signed=False))
            self.proc(request, args, response)

    def request(self, request: ERequest, args: bytes):
        data = b''.join([request.bytes(), args])
        self.client.send(data)
