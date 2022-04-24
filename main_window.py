from PyQt5.QtGui import uic
from threading import Thread
import socket
from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QGroupBox, QFileDialog
from PyQt5.QtGui import QColor, QPalette, QPixmap, QMouseEvent, QCloseEvent

from interaction.protocol import Interactor
from interaction.bundle import Bundle
from interaction.byte_enum import ERequest, EResponse


class MainWindow:
    """
    A wrapper class for PyQt MainWindow.
    It's also a bridge between server socket and clients.
    """
def set_widget_background_color(widget: QWidget, color: QColor):
    palette = widget.palette()
    palette.setColor(QPalette.Window, color)
    widget.setPalette(palette)

    widget.setAutoFillBackground(True)
    widget.show()


def show_image(view: QLabel, data: bytes):
    pixmap = QPixmap()
    if pixmap.loadFromData(data, 'JPEG'):
        if pixmap.width() > pixmap.height():
            pixmap = pixmap.scaledToWidth(view.width())
        elif pixmap.width() < pixmap.height():
            pixmap = pixmap.scaledToHeight(view.height())

        view.setPixmap(pixmap)
    else:
        raise ValueError('Failed to load image.')


class MainWindow(QMainWindow):
    class ClickableLabel(QLabel):
        double_clicked = pyqtSignal(QMouseEvent)

        def mouseDoubleClickEvent(self, a0: QMouseEvent) -> None:
            super().mouseDoubleClickEvent(a0)
            self.double_clicked.emit(a0)
    PORT = 58431
    instance = None

    def __init__(self):
        super(QMainWindow, self).__init__()

        # MainWindow
        self.setObjectName("main_window")
        self.resize(535, 430)
        self.setMinimumSize(QSize(535, 430))
        self.setMaximumSize(QSize(535, 430))

        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")

        # Camera Client
        # # Front Camera
        self.front_camera_view = QLabel(self.central_widget)
        self.front_camera_view.setGeometry(QRect(10, 10, 256, 158))
        self.front_camera_view.setObjectName("front_camera_view")

        self.front_camera_capture_button = QPushButton(self.central_widget)
        self.front_camera_capture_button.setGeometry(QRect(10, 170, 75, 23))
        self.front_camera_capture_button.setObjectName("front_camera_capture_button")

        self.front_camera_label = QLabel(self.central_widget)
        self.front_camera_label.setGeometry(QRect(90, 175, 81, 16))
        self.front_camera_label.setObjectName("front_camera_label")

        # # Rear Camera
        self.rear_camera_view = QLabel(self.central_widget)
        self.rear_camera_view.setGeometry(QRect(270, 10, 256, 158))
        self.rear_camera_view.setObjectName("rear_camera_view")

        self.rear_camera_capture_button = QPushButton(self.central_widget)
        self.rear_camera_capture_button.setGeometry(QRect(270, 170, 75, 23))
        self.rear_camera_capture_button.setObjectName("rear_camera_capture_button")

        self.rear_camera_label = QLabel(self.central_widget)
        self.rear_camera_label.setGeometry(QRect(350, 175, 81, 16))
        self.rear_camera_label.setObjectName("rear_camera_label")

        # Display Client
        # # Camera
        self.display_camera_view = QLabel(self.central_widget)
        self.display_camera_view.setGeometry(QRect(10, 210, 256, 158))
        self.display_camera_view.setObjectName("display_camera_view")

        self.display_camera_capture_button = QPushButton(self.central_widget)
        self.display_camera_capture_button.setGeometry(QRect(10, 370, 75, 23))
        self.display_camera_capture_button.setObjectName("display_camera_capture_button")

        self.display_camera_label = QLabel(self.central_widget)
        self.display_camera_label.setGeometry(QRect(90, 375, 231, 16))
        self.display_camera_label.setObjectName("display_camera_label")

        # # Displaying Image
        self.image_path_label = MainWindow.ClickableLabel(self.central_widget)
        self.image_path_label.setGeometry(QRect(90, 400, 231, 16))
        self.image_path_label.setObjectName("image_path_label")

        self.send_image_to_display_button = QPushButton(self.central_widget)
        self.send_image_to_display_button.setGeometry(QRect(10, 395, 75, 23))
        self.send_image_to_display_button.setObjectName("send_image_to_display_button")

        # Client States
        self.client_state_group_box = QGroupBox(self.central_widget)
        self.client_state_group_box.setGeometry(QRect(280, 210, 161, 91))
        self.client_state_group_box.setObjectName("client_state_group_box")

        self.camera_state_view = QWidget(self.client_state_group_box)
        self.camera_state_view.setGeometry(QRect(10, 30, 16, 16))
        self.camera_state_view.setObjectName("camera_state_view")

        self.camera_state_label = QLabel(self.client_state_group_box)
        self.camera_state_label.setGeometry(QRect(30, 30, 81, 16))
        self.camera_state_label.setObjectName("camera_state_label")

        self.display_state_view = QWidget(self.client_state_group_box)
        self.display_state_view.setGeometry(QRect(10, 60, 16, 16))
        self.display_state_view.setObjectName("display_state_view")

        self.display_state_label = QLabel(self.client_state_group_box)
        self.display_state_label.setGeometry(QRect(30, 60, 81, 16))
        self.display_state_label.setObjectName("display_state_label")

        # Post Refactoring Process
        self.setCentralWidget(self.central_widget)

        self.init_translation()
        self.init_components()
        QMetaObject.connectSlotsByName(self)
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
        MainWindow.instance = self
    def init_translation(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("main_window", "Solubility Measurement"))

        self.front_camera_capture_button.setText(_translate("main_window", "Capture"))
        self.front_camera_label.setText(_translate("main_window", "Front Camera"))

        self.rear_camera_capture_button.setText(_translate("main_window", "Capture"))
        self.rear_camera_label.setText(_translate("main_window", "Rear Camera"))

        self.display_camera_capture_button.setText(_translate("main_window", "Capture"))
        self.display_camera_label.setText(_translate("main_window", "Display Camera"))

        self.send_image_to_display_button.setText(_translate("main_window", "Display"))
        self.image_path_label.setText(_translate("main_window", "(Double click here to browse an image.)"))

        self.client_state_group_box.setTitle(_translate("main_window", "Clients"))
        self.camera_state_label.setText(_translate("main_window", "Camera"))
        self.display_state_label.setText(_translate("main_window", "Display"))

    def init_components(self):
        set_widget_background_color(self.front_camera_view, MainWindow.Theme.GRAY.value)
        set_widget_background_color(self.rear_camera_view, MainWindow.Theme.GRAY.value)
        set_widget_background_color(self.display_camera_view, MainWindow.Theme.GRAY.value)

        set_widget_background_color(self.camera_state_view, MainWindow.Theme.STATE_AVAILABLE.value)
        set_widget_background_color(self.display_state_view, MainWindow.Theme.STATE_UNAVAILABLE.value)

        self.front_camera_capture_button.setEnabled(False)
        self.rear_camera_capture_button.setEnabled(False)
        self.display_camera_capture_button.setEnabled(False)
        self.send_image_to_display_button.setEnabled(False)
        set_widget_background_color(self.camera_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)
        set_widget_background_color(self.display_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)

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
