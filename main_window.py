from PyQt6 import uic
from PyQt6.QtCore import QThread, pyqtSlot
from threading import Thread
import socket

from interaction.bundle import Bundle
from interaction.protocol import ERequest, EResponse, Interactor


class MainWindow(QThread):
    """
    A wrapper class for PyQt MainWindow.
    It's also a bridge between server socket and clients.
    """
    PORT = 58431

    def __init__(self):
        super(MainWindow, self).__init__()

        form_class, window_class = uic.loadUiType("MainWindow.ui")
        self.window = window_class()
        self.form = form_class()
        self.form.setupUi(self.window)

        self.camera_handler = None
        self.display_handler = None
        self.request_id = 0
        self.request_data_map = {}

        # start socket thread
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((socket.INADDR_ANY, MainWindow.PORT))

        def listen():
            while self.camera_handler is None or self.display_handler is None:
                ''' 
                Accept both camera and display handler.
                If occupied role is proposed, send error.
                If unknown role is proposed, send error.
                If normal(newly role occupied), send ok.
                '''
                # accept client to evaluate
                client, address = self.server.accept()
                data = client.recv(Interactor.BUFFER_SIZE)
                _, role, _, _ = Bundle.from_bytes(data)

                # evaluate proposed role
                response: EResponse
                if role == ERequest.CAMERA:
                    if self.camera_handler is not None:
                        response = EResponse.ERROR
                    else:
                        camera_handler = Interactor(client, MainWindow.handle_camera)
                        camera_handler.received_signal.connect(self.digest_response)
                        response = EResponse.OK
                        MainWindow.handle_camera(role, b'')
                elif role == ERequest.DISPLAY:
                    if self.camera_handler is not None:
                        response = EResponse.ERROR
                    else:
                        display_handler = Interactor(client, MainWindow.handle_display)
                        display_handler.received_signal.connect(self.digest_response)
                        response = EResponse.OK
                        MainWindow.handle_display(role, b'')
                else:
                    response = EResponse.ERROR

                client.send(response.bytes())
        Thread(target=listen, args=()).start()

    def show(self):
        self.window.show()

    # region Networking

    def request(self, request: ERequest, args: bytes) -> None:
        """
        Request to an appropriate client with its flag and arguments.
        :param request: The request flag.
        :param args: The arguments for the request.
        :return: None
        """
        interactor: Interactor
        if request.is_for_camera():
            interactor = self.camera_handler
        elif request.is_for_display():
            interactor = self.display_handler
        else:
            raise ValueError('Unreachable scope reached. Check EResponse values.')

        self.request_id += 1
        if self.request_id > Interactor.MAX_REQ_ID:
            self.request_id = 0

        self.request_data_map[self.request_id] = (request, args)
        interactor.request(self.request_id, request, args)

    @pyqtSlot(Bundle)
    def digest_response(self, request_id: int, response: EResponse, args: bytes) -> None:
        """
        Handles response for host request.
        :param request_id: The ID of the host request.
        :param response: The response flag.
        :param args: The arguments for the request.
        :return: None
        """
        request, request_args = self.request_data_map[request_id]
        del self.request_data_map[request_id]
        # TODO: digest_response()

    @staticmethod
    def handle_camera(request: ERequest, args: bytes) -> EResponse:
        """
        Handles request from camera client.
        :param request: The request flag.
        :param args: The arguments for the request.
        :return: Response flag for the request.
        """
        response: EResponse = EResponse.NONE
        if request == ERequest.CAMERA:
            response = EResponse.OK
        # TODO: other requests
        else:
            response = EResponse.REJECT

        return response

    @staticmethod
    def handle_display(request: ERequest, args: bytes) -> EResponse:
        """
        Handles request from display client.
        :param request: The request flag.
        :param args: The arguments for the request.
        :return: Response flag for the request.
        """
        response: EResponse = EResponse.NONE
        if request == ERequest.DISPLAY:
            response = EResponse.OK
        # TODO: other requests
        else:
            response = EResponse.REJECT

        return response

    # endregion
