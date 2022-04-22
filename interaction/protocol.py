from interaction.bundle import Bundle
from typing import Callable
import socket
from PyQt6.QtCore import QThread


class Interactor(QThread):
    """
    An interactor thread to a client socket.
    It sends, receives request or response to pass it to the MainWindow.
    """
    BUFFER_SIZE = 1024
    MAX_REQ_ID = 254
    CLIENT_REQ_ID = 255

    def __init__(self,
                 client: socket.socket,
                 request_handler: Callable[[Bundle], Bundle],
                 response_handler: Callable[[Bundle], None]):
        super(Interactor, self).__init__()

        self.client = client
        self.request_handler = request_handler
        self.response_handler = response_handler

    def run(self) -> None:
        """
        Main routine for this thread.
        :return: None
        """
        while True:
            # receive data
            # TODO: receiving all data from the socket
            data = self.client.recv(4)
            length = int.from_bytes(data, byteorder='big')
            print('Estimated size:', length)

            data = b''
            while len(data) < length:
                buffer = self.client.recv(length)
                data += buffer
            print('Received size:', len(data))

            bundle = Bundle.from_bytes(data)
            request_id, request, args, response = bundle

            if request_id == Interactor.CLIENT_REQ_ID:
                # handle it if it's a request
                response_bundle = self.request_handler(bundle)
                self.client.send(response_bundle.bytes())
            else:
                # if response, send bundle to window via signal
                self.response_handler(bundle)

    def request(self, bundle: Bundle) -> None:
        """
        Send a request with specified request ID.
        :param bundle: The request bundle
        :return: None
        """
        if bundle.request_id > Interactor.MAX_REQ_ID:
            raise ValueError('Out of request id range.')

        self.client.send(bundle.bytes())
