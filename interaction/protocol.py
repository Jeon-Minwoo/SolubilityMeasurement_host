from interaction.bundle import Bundle
from typing import Callable
import socket
from threading import Thread


class Interactor(Thread):
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
                 response_handler: Callable[[Bundle], None],
                 on_disconnected: Callable[[], None]):
        super(Interactor, self).__init__()

        self.client = client
        self.request_handler = request_handler
        self.response_handler = response_handler
        self.on_disconnected = on_disconnected
        self.stop = True

    def run(self) -> None:
        """
        Main routine for this thread.
        :return: None
        """
        self.stop = False
        while not self.stop:
            # receive data
            data = self.client.recv(4)
            length = int.from_bytes(data, byteorder='big')
            print('Estimated size:', length)

            data = b''
            while len(data) < length:
                buffer = self.client.recv(length)
                data += buffer
            print('Received size:', len(data))

            if len(data) != 0:
                bundle = Bundle.from_bytes(data)
                request_id, request, args, response = bundle

                if request_id == Interactor.CLIENT_REQ_ID:
                    # handle it if it's a request
                    response_bundle = self.request_handler(bundle)
                    self.send_bundle(response_bundle)
                else:
                    # if response, send bundle to window via signal
                    self.response_handler(bundle)
            else:
                break
        self.on_disconnected()

    def request(self, bundle: Bundle) -> None:
        """
        Send a request with specified request ID.
        :param bundle: The request bundle
        :return: None
        """
        if bundle.request_id > Interactor.MAX_REQ_ID:
            raise ValueError('Out of request id range.')

        self.send_bundle(bundle)

    def send_bundle(self, bundle: Bundle) -> None:
        data = bundle.bytes()
        length_bytes = int.to_bytes(len(data), length=4, byteorder='big')

        self.client.send(length_bytes)
        self.client.send(bundle.bytes())

    def interrupt(self):
        self.stop = True
