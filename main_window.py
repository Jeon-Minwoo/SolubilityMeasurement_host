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
                bundle = Bundle.from_bytes(data)
                role = bundle.request

                # evaluate proposed role
                if role == ERequest.CAMERA:
                    if self.camera_handler is not None:
                        bundle.response = EResponse.ERROR
                    else:
                        camera_handler = Interactor(client, MainWindow.handle_client_request)
                        camera_handler.received_signal.connect(self.digest_response)
                        bundle.response = EResponse.OK
                elif role == ERequest.DISPLAY:
                    if self.display_handler is not None:
                        bundle.response = EResponse.ERROR
                    else:
                        display_handler = Interactor(client, MainWindow.handle_client_request)
                        display_handler.received_signal.connect(self.digest_response)
                        bundle.response = EResponse.OK
                else:
                    bundle.response = EResponse.ERROR

                MainWindow.handle_client_request(bundle)
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

        interactor.request(self.request_id, request, args)

    @pyqtSlot(Bundle)
    def digest_response(self, bundle: Bundle) -> None:
        """
        Handles response for host request.
        :param bundle: The bundle instance for the request.
        :return: None
        """
        # TODO: digest_response()
        if bundle.request == ERequest.CAMERA_TAKE_PICTURE:
            pass
        elif bundle.request == ERequest.CAMERA_TOGGLE_TORCH:
            pass
        elif bundle.request == ERequest.DISPLAY_TAKE_PICTURE:
            pass
        elif bundle.request == ERequest.DISPLAY_SHOW_PICTURE:
            pass

    @staticmethod
    def handle_client_request(bundle: Bundle) -> Bundle:
        """
        Handles request from camera client.
        :param bundle: The bundle for the request.
        :return: Response flag for the request.
        """
        if bundle.request == ERequest.ANY_QUIT:
            bundle.response = EResponse.ACK
            # TODO: show in dashboard
        else:
            bundle.response = EResponse.REJECT

        return bundle

    # endregion
