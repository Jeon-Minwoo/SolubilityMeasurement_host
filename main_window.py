from PyQt6 import uic
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any
import socket
from protocol import resolve_request, ERequest, EResponse, RequestHandler


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
        data = client.recv(RequestHandler.BUFFER_SIZE)
        request, args = resolve_request(data)

        return client, args, request

    def run(self):
        client1, addr1, role1 = self.accept()
        client2, addr2, role2 = self.accept()

         # TODO: networking

    # endregion
