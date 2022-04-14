from byte_enum import ERequest, EResponse
from bundle import Bundle
from typing import Callable
import socket
from PyQt6.QtCore import QThread, pyqtSignal


class Interactor(QThread):
    """
    An interactor thread to a client socket.
    It sends, receives request or response to pass it to the MainWindow.
    """
    BUFFER_SIZE = 1024
    MAX_REQ_ID = 0xFF
    CLIENT_REQ_ID = -1
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
        """
        while True:
            # receive data
            data = self.client.recv(Interactor.BUFFER_SIZE)
            bundle = Bundle.from_bytes(data)
            request_id, request, args, response = bundle

            if request_id == Interactor.CLIENT_REQ_ID:
                # handle it if it's a request
                response = self.handler(request, args)
                self.client.send(response.bytes())
                bundle.response = response
            else:
                # if response, send bundle to window via signal
                self.received_signal.emit(request_id, response, args)

    def request(self, request_id: int, request: ERequest, args: bytes) -> None:
        """
        Send a request with specified request ID.
        :param request_id: The ID of a new request.
        :param request: The request flag.
        :param args: The arguments for the request.
        :return: None
        """
        if request_id > Interactor.MAX_REQ_ID:
            raise ValueError('Out of request id range.')

        bundle = Bundle(request_id, request, args=args)
        self.client.send(bundle.bytes())
