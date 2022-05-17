import os
import io
from typing import Any
from enum import Enum
import socket

import cv2.cv2 as cv2
from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QGroupBox, QFileDialog
from PyQt5.QtGui import QColor, QPalette, QPixmap, QMouseEvent, QCloseEvent

import numpy as np
from PIL import Image

from interruptable_thread import InterruptableThread
from interaction.protocol import Interactor
from interaction.bundle import Bundle
from interaction.byte_enum import ERequest, EResponse


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
    class Theme(Enum):
        GRAY = QColor(0x2B2B2B)

        RED = QColor(0xFF0000)
        GREEN = QColor(0x00FF00)
        BLUE = QColor(0x0000FF)

        STATE_AVAILABLE = QColor(0x33AA33)
        STATE_UNAVAILABLE = QColor(0xAA3333)

    class ClickableLabel(QLabel):
        double_clicked = pyqtSignal(QMouseEvent)

        def mouseDoubleClickEvent(self, a0: QMouseEvent) -> None:
            super().mouseDoubleClickEvent(a0)
            # noinspection PyUnresolvedReferences
            self.double_clicked.emit(a0)

    PORT = 58431
    instance = None

    # noinspection PyTypeChecker
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
        self.torch_toggle_button = QPushButton(self.central_widget)
        self.torch_toggle_button.setGeometry(QRect(280, 210, 75, 23))
        self.torch_toggle_button.setObjectName("torch_toggle_button")

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
        self.client_state_group_box.setGeometry(QRect(280, 238, 161, 91))
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
        self.init_events()
        QMetaObject.connectSlotsByName(self)

        # Starting Socket Interaction
        self.camera_handler: Interactor = None
        self.display_handler: Interactor = None
        self.request_id = 0
        self.capture_requests = {}
        self.image_path = ''

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', MainWindow.PORT))
        self.server.listen(10)

        self.listener = InterruptableThread(MainWindow.listen, (self,))
        self.listener.start()

        MainWindow.instance = self

    def increase_request_id(self) -> int:
        self.request_id += 1
        if self.request_id > Interactor.MAX_REQ_ID:
            self.request_id = 0
        return self.request_id

    def init_translation(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("main_window", "Solubility Measurement"))

        self.torch_toggle_button.setText(_translate("main_window", "Torch"))

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

        self.torch_toggle_button.setEnabled(False)
        self.front_camera_capture_button.setEnabled(False)
        self.rear_camera_capture_button.setEnabled(False)
        self.display_camera_capture_button.setEnabled(False)
        self.send_image_to_display_button.setEnabled(False)
        set_widget_background_color(self.camera_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)
        set_widget_background_color(self.display_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)

    def init_events(self):
        def request_toggle_torch(_: QMouseEvent):
            self.torch_toggle_button.setEnabled(False)
            bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TOGGLE_TORCH)
            self.camera_handler.request(bundle)
        self.torch_toggle_button.clicked.connect(request_toggle_torch)

        def request_front_capture(_: QMouseEvent):
            self.front_camera_capture_button.setEnabled(False)
            self.rear_camera_capture_button.setEnabled(False)
            bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TAKE_PICTURE, bytes([1]))
            self.camera_handler.request(bundle)
            self.capture_requests[bundle.request_id] = 1
        self.front_camera_capture_button.clicked.connect(request_front_capture)

        def request_rear_capture(_: QMouseEvent):
            self.front_camera_capture_button.setEnabled(False)
            self.rear_camera_capture_button.setEnabled(False)
            bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TAKE_PICTURE, bytes([0]))
            self.camera_handler.request(bundle)
            self.capture_requests[bundle.request_id] = 0
        self.rear_camera_capture_button.clicked.connect(request_rear_capture)

        def request_display_capture(_: QMouseEvent):
            self.display_camera_capture_button.setEnabled(False)
            bundle = Bundle(self.increase_request_id(), ERequest.DISPLAY_TAKE_PICTURE)
            self.display_handler.request(bundle)
        self.display_camera_capture_button.clicked.connect(request_display_capture)

        def request_displaying_image(_: QMouseEvent):
            if os.path.exists(self.image_path):
                # self.send_image_to_display_button.setEnabled(False)
                with open(self.image_path, 'rb') as file:
                    image = file.read()
                bundle = Bundle(self.increase_request_id(), ERequest.DISPLAY_SHOW_PICTURE, image)
                self.display_handler.request(bundle)
            else:
                self.image_path_label.setText("File doesn't exist.")
        self.send_image_to_display_button.clicked.connect(request_displaying_image)

        def browse_image(_: QMouseEvent):
            dialog = QFileDialog(caption='Open image', directory='.', filter='Image files (*.jpg *.jpeg, *.png)')
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.exec_()
            file_names = dialog.selectedFiles()
            if len(file_names) == 0:
                return
            self.image_path = file_names[0]

            file_name = self.image_path.split(os.sep)[-1]
            self.image_path_label.setText(file_name)

            self.send_image_to_display_button.setEnabled(True)

        # noinspection PyUnresolvedReferences
        self.image_path_label.double_clicked.connect(browse_image)

    def listen(self):
        print('Listen: Start listening')
        while True:
            # accept client to evaluate
            try:
                client, address = self.server.accept()
                print(f'Listen: accept, {address}')
                client.recv(4)  # skip message length
                data = client.recv(Interactor.BUFFER_SIZE)
                bundle = Bundle.from_bytes(data)
                role = bundle.request

                # evaluate proposed role
                if role == ERequest.CAMERA:
                    if self.camera_handler is not None:
                        print(f'Listen: camera, error')
                        bundle.response = EResponse.ERROR
                    else:
                        print(f'Listen: camera, ok')

                        def on_disconnected():
                            self.camera_handler = None
                            self.torch_toggle_button.setEnabled(False)
                            self.rear_camera_capture_button.setEnabled(False)
                            self.front_camera_capture_button.setEnabled(False)
                            set_widget_background_color(self.camera_state_view,
                                                        MainWindow.Theme.STATE_UNAVAILABLE.value)
                            print('Camera disconnected')

                        self.camera_handler = Interactor(client,
                                                         MainWindow.handle_client_request,
                                                         MainWindow.digest_response,
                                                         on_disconnected)
                        self.camera_handler.start()

                        self.torch_toggle_button.setEnabled(True)
                        self.rear_camera_capture_button.setEnabled(True)
                        self.front_camera_capture_button.setEnabled(True)
                        set_widget_background_color(self.camera_state_view,
                                                    MainWindow.Theme.STATE_AVAILABLE.value)
                        bundle.response = EResponse.OK
                elif role == ERequest.DISPLAY:
                    if self.display_handler is not None:
                        print(f'Listen: display, error')
                        bundle.response = EResponse.ERROR
                    else:
                        print(f'Listen: display, ok')

                        def on_disconnected():
                            self.display_handler = None
                            self.display_camera_capture_button.setEnabled(False)
                            self.send_image_to_display_button.setEnabled(False)
                            set_widget_background_color(self.display_state_view,
                                                        MainWindow.Theme.STATE_UNAVAILABLE.value)
                            print('Display disconnected')

                        self.display_handler = Interactor(client,
                                                          MainWindow.handle_client_request,
                                                          MainWindow.digest_response,
                                                          on_disconnected)
                        self.display_handler.start()

                        self.display_camera_capture_button.setEnabled(True)
                        set_widget_background_color(self.display_state_view,
                                                    MainWindow.Theme.STATE_AVAILABLE.value)
                        bundle.response = EResponse.OK
                else:
                    print(f'Listen: unknown')
                    bundle.response = EResponse.ERROR

                MainWindow.handle_client_request(bundle)
            except OSError:
                break

    def closeEvent(self, e: QCloseEvent) -> None:
        if self.camera_handler is not None:
            self.camera_handler.interrupt()
        if self.display_handler is not None:
            self.display_handler.interrupt()
        self.listener.interrupt()
        self.server.close()

        super(QMainWindow, self).closeEvent(e)

    @staticmethod
    def digest_response(bundle: Bundle) -> None:
        """
        Handles response for host request.
        :param: bundle: The bundle instance for the request.
        :return: None
        """
        window: MainWindow = MainWindow.instance
        if window is None:
            return

        print(f'ClientResp: {bundle}')
        if bundle.request == ERequest.CAMERA_TAKE_PICTURE:
            cam_id = window.capture_requests[bundle.request_id]
            del window.capture_requests[bundle.request_id]

            is_valid = True
            if cam_id == 0:
                show_image(window.rear_camera_view, bundle.args)
            elif cam_id == 1:
                show_image(window.front_camera_view, bundle.args)
            else:
                is_valid = False

            if is_valid:
                window.front_camera_capture_button.setEnabled(True)
                window.rear_camera_capture_button.setEnabled(True)
                img = Image.open(io.BytesIO(bundle.args))
                img = np.array(img)
                MainWindow.process_image(img)
        elif bundle.request == ERequest.CAMERA_TOGGLE_TORCH:
            print('Toggle OK')
            window.torch_toggle_button.setEnabled(True)
        elif bundle.request == ERequest.DISPLAY_TAKE_PICTURE:
            show_image(window.display_camera_view, bundle.args)
            img = Image.open(io.BytesIO(bundle.args))
            img = np.array(img)
            MainWindow.process_image(img)
            window.display_camera_capture_button.setEnabled(True)
        elif bundle.request == ERequest.DISPLAY_SHOW_PICTURE:
            if bundle.response == EResponse.OK:
                window.image_path_label.setText('Image displayed.')
                window.image_path = ''
            elif bundle.response == EResponse.ERROR:
                window.image_path_label.setText('Error occurred.')
        else:
            print('Unknown')
        print()

    @staticmethod
    def handle_client_request(bundle: Bundle) -> Bundle:
        """
        Handles request from camera client.
        :param: bundle: The bundle for the request.
        :return: Response flag for the request.
        """
        if bundle.request == ERequest.ANY_QUIT:
            bundle.response = EResponse.ACK
        else:
            bundle.response = EResponse.REJECT

        print(f'ClientReq: {bundle}')
        return bundle

    @staticmethod
    def process_image(image: np.array) -> Any:
        # TODO: process image

        import PIL
        img = PIL.Image.fromarray(image)
        img.save('./img.jpeg')
        pass
