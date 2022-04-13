from PyQt6 import uic
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any
import socket
from protocol import resolve_request, ERequest, EResponse, Interactor


class MainWindow(QThread):
    proc = pyqtSignal(# TODO: parameters)

    def __init__(self):
        super(MainWindow, self).__init__()

        form_class, window_class = uic.loadUiType("MainWindow.ui")
        self.window = window_class()
        self.form = form_class()
        self.form.setupUi(self.window)

        # start socket thread
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.start()

    def show(self):
        self.window.show()

    # region Networking

    def accept(self) -> (socket.socket, Any, ERequest):
        client, addr = self.server.accept()
        data = client.recv(Interactor.BUFFER_SIZE)
        request, args = resolve_request(data)

        return client, args, request

    def run(self):
        camera_handler, display_handler = None, None

        while camera_handler is None or display_handler is None:
            ''' 
            Accept both camera and display handler.
            If occupied role is proposed, send error.
            If unknown role is proposed, send error.
            If normal(newly role occupied), send ok.
            '''
            client, address, role = self.accept()

            response: EResponse
            if role == ERequest.CAMERA:
                if camera_handler is not None:
                    response = EResponse.ERROR
                else:
                    camera_handler = Interactor(client, MainWindow.handle_camera)
                    response = EResponse.OK
            elif role == ERequest.DISPLAY:
                if camera_handler is not None:
                    response = EResponse.ERROR
                else:
                    display_handler = Interactor(client, MainWindow.handle_display)
                    response = EResponse.OK
            else:
                response = EResponse.ERROR
            client.send(response.bytes())

         # TODO: networking

    @staticmethod
    def handle_camera(request: ERequest, args: bytes) -> EResponse:
        pass

    @staticmethod
    def handle_display(request: ERequest, args: bytes) -> EResponse:
        pass

    # endregion
