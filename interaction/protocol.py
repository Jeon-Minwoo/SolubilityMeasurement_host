from interaction.bundle import Bundle
from typing import Callable
import socket
from PyQt6.QtCore import QThread, pyqtSignal


class Interactor(QThread):
    """
    An interactor thread to a client socket.
    It sends, receives request or response to pass it to the MainWindow.
    """
    BUFFER_SIZE = 1024
    MAX_REQ_ID = 254
    CLIENT_REQ_ID = 255
    received_signal = pyqtSignal(Bundle)

    def __init__(self,
                 client: socket.socket,
                 handler: Callable[[Bundle], Bundle]):
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
            data = b''
            while True:
                buffer = self.client.recv(Interactor.BUFFER_SIZE)
                if len(data) > 0:
                    data += buffer
                else:
                    break

            bundle = Bundle.from_bytes(data)
            request_id, request, args, response = bundle

            if request_id == Interactor.CLIENT_REQ_ID:
                # handle it if it's a request
                response_bundle = self.handler(bundle)
                self.client.send(response_bundle.bytes())
            else:
                # if response, send bundle to window via signal
                self.received_signal.emit(bundle)

    def request(self, bundle: Bundle) -> None:
        """
        Send a request with specified request ID.
        :param bundle: The request bundle
        :return: None
        """
        if bundle.request_id > Interactor.MAX_REQ_ID:
            raise ValueError('Out of request id range.')

        self.client.send(bundle.bytes())
