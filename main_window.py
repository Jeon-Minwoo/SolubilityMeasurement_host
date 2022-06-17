from audioop import cross
import os
import io
from typing import Any
from enum import Enum
import socket
import torch

from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QGroupBox, QFileDialog, QCheckBox, QLineEdit, QComboBox, QMessageBox
from PyQt5.QtGui import QColor, QPalette, QPixmap, QMouseEvent, QCloseEvent


import numpy as np
import cv2
from PIL import Image

from interruptable_thread import InterruptableThread
from interaction.protocol import Interactor
from interaction.bundle import Bundle
from interaction.byte_enum import ERequest, EResponse
from image_process.all_image_cls import image_clf
from classifier_svm import svm_


def set_widget_background_color(widget: QWidget, color: QColor):
    palette = widget.palette()
    palette.setColor(QPalette.Window, color)
    widget.setPalette(palette)

    widget.setAutoFillBackground(True)
    widget.show()


def show_image(view: QLabel, data: bytes):
    pixmap = QPixmap()
    if pixmap.loadFromData(data, 'JPEG'):
        # if pixmap.width() > pixmap.height():
        #     pixmap = pixmap.scaledToWidth(view.width())
        # elif pixmap.width() < pixmap.height():
        #     pixmap = pixmap.scaledToHeight(view.height())
        pixmap = pixmap.scaledToWidth(view.width())
        #pixmap = pixmap.scaledToHeight(view.height())
        view.setPixmap(pixmap)
    else:
        raise ValueError('Failed to load image.')

def make_cross_pattern(img: np):
    cross_pattern = img.copy()
    cross_pattern = cv2.line(cross_pattern, (0,720), (1920,720), (0,255,0),2,cv2.LINE_AA)
    cross_pattern = cv2.line(cross_pattern, (960,0), (960,1440), (0,255,0),2,cv2.LINE_AA)
    return cross_pattern

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
        self.resize(1000, 1050)
        self.setMinimumSize(QSize(1000, 965))
        self.setMaximumSize(QSize(1000, 965))

        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")

        # Camera Client
        self.torch_toggle_button = QPushButton(self.central_widget)
        self.torch_toggle_button.setGeometry(QRect(550, 880, 75, 23))
        self.torch_toggle_button.setObjectName("torch_toggle_button")

        # # Front Camera
        self.front_camera_view = QLabel(self.central_widget)
        self.front_camera_view.setGeometry(QRect(10, 10, 384, 250))
        self.front_camera_view.setObjectName("front_camera_view")

        self.front_camera_capture_button = QPushButton(self.central_widget)
        self.front_camera_capture_button.setGeometry(QRect(10, 270, 75, 23))
        self.front_camera_capture_button.setObjectName("front_camera_capture_button")

        self.front_camera_label = QLabel(self.central_widget)
        self.front_camera_label.setGeometry(QRect(90, 275, 101, 16))
        self.front_camera_label.setObjectName("front_camera_label")

        # # Rear Camera
        self.rear_camera_view = QLabel(self.central_widget)
        self.rear_camera_view.setGeometry(QRect(16, 300, 768, 576))
        self.rear_camera_view.setObjectName("rear_camera_view")

        self.rear_camera_capture_button = QPushButton(self.central_widget)
        self.rear_camera_capture_button.setGeometry(QRect(10, 880, 75, 23))
        self.rear_camera_capture_button.setObjectName("rear_camera_capture_button")

        self.rear_camera_label = QLabel(self.central_widget)
        self.rear_camera_label.setGeometry(QRect(96, 885, 91, 16))
        self.rear_camera_label.setObjectName("rear_camera_label")

        # Display Client
        # # Camera
        self.display_camera_view = QLabel(self.central_widget)
        self.display_camera_view.setGeometry(QRect(406, 10, 384, 250))
        self.display_camera_view.setObjectName("display_camera_view")

        self.display_camera_capture_button = QPushButton(self.central_widget)
        self.display_camera_capture_button.setGeometry(QRect(406, 270, 75, 23))
        self.display_camera_capture_button.setObjectName("display_camera_capture_button")

        self.display_camera_label = QLabel(self.central_widget)
        self.display_camera_label.setGeometry(QRect(486, 275, 231, 16))
        self.display_camera_label.setObjectName("display_camera_label")


        # # Displaying Image
        self.image_path_label = MainWindow.ClickableLabel(self.central_widget)
        self.image_path_label.setGeometry(QRect(90, 915, 271, 16))
        self.image_path_label.setObjectName("image_path_label")

        self.send_image_to_display_button = QPushButton(self.central_widget)
        self.send_image_to_display_button.setGeometry(QRect(10, 910, 75, 23))
        self.send_image_to_display_button.setObjectName("send_image_to_display_button")

        ### Calibration Mode
        self.calibration_ck_box = QCheckBox(self.central_widget)
        self.calibration_ck_box.setGeometry(QRect(360, 915, 150, 16))
        self.calibration_ck_box.setObjectName("calibration_ck_box")

        self.bg_display_button = QPushButton(self.central_widget)
        self.bg_display_button.setGeometry(QRect(250, 940, 91, 23))
        self.bg_display_button.setObjectName("bg_display_button")
        
        self.save_button = QPushButton(self.central_widget)
        self.save_button.setGeometry(QRect(550, 910, 75, 23))
        self.save_button.setObjectName("save_button")

        self.save_path_label = MainWindow.ClickableLabel(self.central_widget)
        self.save_path_label.setGeometry(QRect(10, 940, 231, 16))
        self.save_path_label.setObjectName("save_path_label")

        self.save_filename_lineedit = QLineEdit(self.central_widget)
        self.save_filename_lineedit.setGeometry(QRect(350, 940, 271, 20))
        self.save_filename_lineedit.setObjectName("save_filename_lineedit")

        # Client States
        self.client_state_group_box = QGroupBox(self.central_widget)
        self.client_state_group_box.setGeometry(QRect(630, 880, 161, 81))
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

        # Feature Groupbox
        self.Feature_groupbox = QGroupBox(self.central_widget)
        self.Feature_groupbox.setGeometry(QRect(790, 600, 201, 361))
        self.Feature_groupbox.setObjectName("Feature_groupbox")
        
        self.supp_ratio_label = QLabel(self.Feature_groupbox)
        self.supp_ratio_label.setGeometry(QRect(10, 20, 71, 16))
        self.supp_ratio_label.setObjectName("supp_ratio_label")
        self.mmg_label = QLabel(self.Feature_groupbox)
        self.mmg_label.setGeometry(QRect(10, 45, 71, 16))
        self.mmg_label.setObjectName("mmg_label")
        self.msg_label = QLabel(self.Feature_groupbox)
        self.msg_label.setGeometry(QRect(10, 70, 64, 15))
        self.msg_label.setObjectName("msg_label")
        self.smg_label = QLabel(self.Feature_groupbox)
        self.smg_label.setGeometry(QRect(10, 95, 64, 15))
        self.smg_label.setObjectName("smg_label")
        self.ssg_label = QLabel(self.Feature_groupbox)
        self.ssg_label.setGeometry(QRect(10, 120, 64, 15))
        self.ssg_label.setObjectName("ssg_label")
        self.curve_a_label = QLabel(self.Feature_groupbox)
        self.curve_a_label.setGeometry(QRect(10, 145, 64, 15))
        self.curve_a_label.setObjectName("curve_a_label")
        self.curve_b_label = QLabel(self.Feature_groupbox)
        self.curve_b_label.setGeometry(QRect(10, 170, 64, 15))
        self.curve_b_label.setObjectName("curve_b_label")
        self.curve_c_label = QLabel(self.Feature_groupbox)
        self.curve_c_label.setGeometry(QRect(10, 195, 64, 15))
        self.curve_c_label.setObjectName("curve_c_label")
        self.std_range_label = QLabel(self.Feature_groupbox)
        self.std_range_label.setGeometry(QRect(10, 220, 64, 15))
        self.std_range_label.setObjectName("std_range_label")
        self.gradient_label = QLabel(self.Feature_groupbox)
        self.gradient_label.setGeometry(QRect(10, 245, 64, 15))
        self.gradient_label.setObjectName("gradient_label")
        self.output_label = QLabel(self.Feature_groupbox)
        self.output_label.setGeometry(QRect(10, 340, 64, 15))
        self.output_label.setObjectName("output_label")
        self.supp_ratio_output_label = QLabel(self.Feature_groupbox)
        self.supp_ratio_output_label.setGeometry(QRect(100, 20, 91, 16))
        self.supp_ratio_output_label.setObjectName("supp_ratio_output_label")
        self.mmg_output_label = QLabel(self.Feature_groupbox)
        self.mmg_output_label.setGeometry(QRect(100, 45, 91, 16))
        self.mmg_output_label.setObjectName("mmg_output_label")
        self.msg_output_label = QLabel(self.Feature_groupbox)
        self.msg_output_label.setGeometry(QRect(100, 70, 91, 16))
        self.msg_output_label.setObjectName("msg_output_label")
        self.smg_output_label = QLabel(self.Feature_groupbox)
        self.smg_output_label.setGeometry(QRect(100, 95, 91, 16))
        self.smg_output_label.setObjectName("smg_output_label")
        self.ssg_output_label = QLabel(self.Feature_groupbox)
        self.ssg_output_label.setGeometry(QRect(100, 120, 91, 16))
        self.ssg_output_label.setObjectName("ssg_output_label")
        self.curve_a_output_label = QLabel(self.Feature_groupbox)
        self.curve_a_output_label.setGeometry(QRect(100, 145, 91, 16))
        self.curve_a_output_label.setObjectName("curve_a_output_label")
        self.curve_b_output_label = QLabel(self.Feature_groupbox)
        self.curve_b_output_label.setGeometry(QRect(100, 170, 91, 16))
        self.curve_b_output_label.setObjectName("curve_b_output_label")
        self.curve_c_output_label = QLabel(self.Feature_groupbox)
        self.curve_c_output_label.setGeometry(QRect(100, 195, 91, 16))
        self.curve_c_output_label.setObjectName("curve_c_output_label")
        self.std_range_output_label = QLabel(self.Feature_groupbox)
        self.std_range_output_label.setGeometry(QRect(100, 220, 91, 16))
        self.std_range_output_label.setObjectName("std_range_output_label")
        self.gradient_output_label = QLabel(self.Feature_groupbox)
        self.gradient_output_label.setGeometry(QRect(100, 245, 91, 16))
        self.gradient_output_label.setObjectName("gradient_output_label")
        self.output_output_label = QLabel(self.Feature_groupbox)
        self.output_output_label.setGeometry(QRect(100, 340, 91, 16))
        self.output_output_label.setObjectName("output_output_label")
        self.particle_sum_label = QLabel(self.Feature_groupbox)
        self.particle_sum_label.setGeometry(QRect(10, 270, 81, 16))
        self.particle_sum_label.setObjectName("particle_sum_label")
        self.particle_sum_output_label = QLabel(self.Feature_groupbox)
        self.particle_sum_output_label.setGeometry(QRect(100, 270, 91, 16))
        self.particle_sum_output_label.setObjectName("particle_sum_output_label")
        
        self.processing_button = QPushButton(self.central_widget)
        self.processing_button.setGeometry(QRect(790, 570, 101, 23))
        self.processing_button.setObjectName("processing_button")
        self.classify_button = QPushButton(self.central_widget)
        self.classify_button.setGeometry(QRect(900, 570, 75, 23))
        self.classify_button.setObjectName("classify_button")

        self.bg_select_combobox = QComboBox(self.central_widget)
        self.bg_select_combobox.setGeometry(QRect(790, 540, 101, 22))
        self.bg_select_combobox.setObjectName("bg_select_combobox")
        self.bg_select_combobox.addItem("")
        self.bg_select_combobox.addItem("")

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
        self.calibration_image_path = 'SolubilityMeasurement_host/cal_bg.png'
        self.image_save_path = 'SolubilityMeasurement_host/image'
        self.last_image = None

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', MainWindow.PORT))
        self.server.listen(10)

        self.listener = InterruptableThread(MainWindow.listen, (self,))
        self.listener.start()

        self.bundle = None

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

        self.calibration_ck_box.setText(_translate("main_window", "Calibration mode"))
        self.save_button.setText(_translate("main_window", "Save"))
        self.classify_button.setText(_translate("main_windowset_", "classify"))
        self.bg_display_button.setText(_translate("main_window", "BG Display"))        
        self.save_path_label.setText(_translate("main_window", "(Double click here to set up path.)"))
        self.save_filename_lineedit.setText(_translate("main_window", "(Save file name)"))

        self.client_state_group_box.setTitle(_translate("main_window", "Clients"))
        self.camera_state_label.setText(_translate("main_window", "Camera"))
        self.display_state_label.setText(_translate("main_window", "Display"))

        self.Feature_groupbox.setTitle(_translate("main_window", "Feature/Output"))
        self.supp_ratio_label.setText(_translate("main_window", "supp_ratio"))
        self.mmg_label.setText(_translate("main_window", "mmg"))
        self.msg_label.setText(_translate("main_window", "msg"))
        self.smg_label.setText(_translate("main_window", "smg"))
        self.ssg_label.setText(_translate("main_window", "ssg"))
        self.curve_a_label.setText(_translate("main_window", "curve_a"))
        self.curve_b_label.setText(_translate("main_window", "curve_b"))
        self.curve_c_label.setText(_translate("main_window", "curve_c"))
        self.std_range_label.setText(_translate("main_window", "std_range"))
        self.gradient_label.setText(_translate("main_window", "gradient"))
        self.output_label.setText(_translate("main_window", "output"))
        self.supp_ratio_output_label.setText(_translate("main_window", "0"))
        self.mmg_output_label.setText(_translate("main_window", "0"))
        self.msg_output_label.setText(_translate("main_window", "0"))
        self.smg_output_label.setText(_translate("main_window", "0"))
        self.ssg_output_label.setText(_translate("main_window", "0"))
        self.curve_a_output_label.setText(_translate("main_window", "0"))
        self.curve_b_output_label.setText(_translate("main_window", "0"))
        self.curve_c_output_label.setText(_translate("main_window", "0"))
        self.std_range_output_label.setText(_translate("main_window", "0"))
        self.gradient_output_label.setText(_translate("main_window", "0"))
        self.output_output_label.setText(_translate("main_window", "-"))
        self.processing_button.setText(_translate("main_window", "Processing"))
        self.bg_select_combobox.setItemText(0, _translate("main_window", "White"))
        self.bg_select_combobox.setItemText(1, _translate("main_window", "Check_pattern"))
        self.particle_sum_label.setText(_translate("main_window", "particle_sum"))
        self.particle_sum_output_label.setText(_translate("main_window", "0"))


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
        self.bg_display_button.setEnabled(False)
        self.processing_button.setEnabled(False)
        self.classify_button.setEnabled(False)
        self.save_button.setEnabled(False)

        set_widget_background_color(self.camera_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)
        set_widget_background_color(self.display_state_view,
                                    MainWindow.Theme.STATE_UNAVAILABLE.value)

    def init_events(self):
        def request_toggle_torch(_: QMouseEvent):
            self.torch_toggle_button.setEnabled(False)
            self.bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TOGGLE_TORCH)
            self.camera_handler.request(self.bundle)
        self.torch_toggle_button.clicked.connect(request_toggle_torch)

        def request_front_capture(_: QMouseEvent):
            # self.front_camera_capture_button.setEnabled(False)
            # self.rear_camera_capture_button.setEnabled(False)
            self.bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TAKE_PICTURE, bytes([1]))
            self.camera_handler.request(self.bundle)
            self.capture_requests[self.bundle.request_id] = 1
            self.save_button.setEnabled(True)
            self.processing_button.setEnabled(True)
            self.classify_button.setEnabled(True)
        self.front_camera_capture_button.clicked.connect(request_front_capture)



        def request_rear_capture(_: QMouseEvent):
            # self.front_camera_capture_button.setEnabled(False)
            # self.rear_camera_capture_button.setEnabled(False)
            self.bundle = Bundle(self.increase_request_id(), ERequest.CAMERA_TAKE_PICTURE, bytes([0]))
            print(self.bundle)
            self.camera_handler.request(self.bundle)
            self.capture_requests[self.bundle.request_id] = 0
            self.save_button.setEnabled(True)
            self.processing_button.setEnabled(True)
            self.classify_button.setEnabled(True)
        self.rear_camera_capture_button.clicked.connect(request_rear_capture)

        def request_display_capture(_: QMouseEvent):
            # self.display_camera_capture_button.setEnabled(False)
            self.bundle = Bundle(self.increase_request_id(), ERequest.DISPLAY_TAKE_PICTURE)
            self.display_handler.request(self.bundle)
            self.save_button.setEnabled(True)
            self.processing_button.setEnabled(True)
            self.classify_button.setEnabled(True)
        self.display_camera_capture_button.clicked.connect(request_display_capture)
        
        def request_displaying_image(_: QMouseEvent):
            if os.path.exists(self.image_path):
                #self.send_image_to_display_button.setEnabled(False)
                with open(self.image_path, 'rb') as file:
                    image = file.read()
                self.bundle = Bundle(self.increase_request_id(), ERequest.DISPLAY_SHOW_PICTURE, image)
                self.display_handler.request(self.bundle)
            else:
                self.image_path_label.setText("File doesn't exist.")
        self.send_image_to_display_button.clicked.connect(request_displaying_image)
        
        
        def request_displaying_calibration_image(_: QMouseEvent):
            with open(self.calibration_image_path, 'rb') as file:
                image = file.read()
            self.bundle = Bundle(self.increase_request_id(), ERequest.DISPLAY_SHOW_PICTURE, image)
            self.display_handler.request(self.bundle)
        self.bg_display_button.clicked.connect(request_displaying_calibration_image)
        

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

        def set_up_image_path(_: QMouseEvent):
            dialog = QFileDialog(caption='Setting directory', directory='.')
            dialog.setFileMode(QFileDialog.Directory)
            if dialog.exec_():
                folder_path = dialog.selectedFiles()[0]
            else:
                return
            self.image_save_path = folder_path
            self.save_path_label.setText(folder_path)
        self.save_path_label.double_clicked.connect(set_up_image_path)

        def processing_image(_: QMouseEvent):
            img = Image.open(io.BytesIO(self.last_image))
            img = np.array(img)
            
            #img = np.array(io.BytesIO(self.last_image))
            #img = cv2.imdecode(self.last_image, cv2.IMREAD_COLOR)
            print(img.shape)
            print('start processing')
            clf = image_clf(img)
            if self.bg_select_combobox.currentIndex() == 0:
                result1 = clf.processing_whitebg()
                if result1[2][4] == np.inf:
                    np.nan_to_num(result1[2][4])
                print('end')
                self.mmg_output_label.setText(str(result1[0][0]))
                self.msg_output_label.setText(str(result1[0][1]))
                self.smg_output_label.setText(str(result1[0][2]))
                self.ssg_output_label.setText(str(result1[0][3]))
                self.curve_a_output_label.setText(str(result1[2][0]))
                self.curve_b_output_label.setText(str(result1[2][1]))
                self.curve_c_output_label.setText(str(result1[2][2]))
                self.std_range_output_label.setText(str(result1[2][3]))
                self.gradient_output_label.setText(str(result1[2][4]))
                self.particle_sum_output_label.setText(str(result1[1]))
                
                return result1
            
            elif self.bg_select_combobox.currentIndex() == 1:
                result2 = clf.processing_checkpat()
                print('end')     
                self.supp_ratio_output_label.setText(str(result2))
                return result2
        self.processing_button.clicked.connect(processing_image)
        
        def classify_image(_: QMouseEvent):
            feature = []
            feature.append(float(self.supp_ratio_output_label.text()))
            feature.append(float(self.mmg_output_label.text()))
            feature.append(float(self.msg_output_label.text()))
            feature.append(float(self.smg_output_label.text()))
            feature.append(float(self.ssg_output_label.text()))
            feature.append(float(self.curve_c_output_label.text()))
            feature.append(float(self.std_range_output_label.text()))
            feature.append(float(self.gradient_output_label.text()))
            feature.append(float(self.particle_sum_output_label.text()))
            input = np.array(feature)
            input_torch = torch.FloatTensor(input.reshape(1, -1))
            print(input_torch)
            input_svm = input.reshape(1,-1)
            model_ = svm_()
            output_ = model_.predict(input_svm)
            print(output_)

            if output_[0] == 2:
                self.output_output_label.setText('pass')
            elif output_[0] == 1:
                self.output_output_label.setText('Fail#2')
            elif output_[0] == 0:
                self.output_output_label.setText('Fail#1')
            
            #model = train()
            #output = model(input_torch)
            #print(output)


        self.classify_button.clicked.connect(classify_image)


        def save_image(_: QMouseEvent):
            img = self.last_image
            if img is None:
                reply = self.Warning_event()
                return
            file_name = self.save_filename_lineedit.text()
            file_path = self.image_save_path
            with open(os.path.join(file_path, file_name, '.png'), 'wb') as file:
                file.write(self.last_image)
            # cv2.imwrite(file_path + '/' + file_name + '.png', cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        self.save_button.clicked.connect(save_image)
        
    def Warning_event(self):
        reply = QMessageBox.warning(self, 'No Capture Image Error', 'Try capture image first')
        return reply

    def listen(self):
        print('Listen: Start listening')
        while True:
            # accept client to evaluate
            try:
                client, address = self.server.accept()
                print(f'Listen: accept, {address}')
                client.recv(4)  # skip message length
                data = client.recv(Interactor.BUFFER_SIZE)
                self.bundle = Bundle.from_bytes(data)
                role = self.bundle.request

                # evaluate proposed role
                if role == ERequest.CAMERA:
                    if self.camera_handler is not None:
                        print(f'Listen: camera, error')
                        self.bundle.response = EResponse.ERROR
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
                        self.bundle.response = EResponse.OK
                elif role == ERequest.DISPLAY:
                    if self.display_handler is not None:
                        print(f'Listen: display, error')
                        self.bundle.response = EResponse.ERROR
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
                        self.bg_display_button.setEnabled(True)
                        set_widget_background_color(self.display_state_view,
                                                    MainWindow.Theme.STATE_AVAILABLE.value)
                        self.bundle.response = EResponse.OK
                else:
                    print(f'Listen: unknown')
                    self.bundle.response = EResponse.ERROR

                MainWindow.handle_client_request(self.bundle)
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
                if window.calibration_ck_box.isChecked() == True:
                    pil_img = Image.open(io.BytesIO(bundle.args))
                    cv_img = np.array(pil_img)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
                    cross_pattern = cv_img.copy()
                    cross_pattern = cv2.line(cross_pattern, (0,720), (1920,720), (0,255,0),3,cv2.LINE_AA)
                    cross_pattern = cv2.line(cross_pattern, (960,0), (960,1440), (0,255,0),3,cv2.LINE_AA)
                    cross_grid_img = cross_pattern
                    data = cv2.imencode('.JPEG', cross_grid_img)[1].tobytes()
                    show_image(window.rear_camera_view, data)
                # if window.save_mode_ck_box.isChecked() == True:
                #     file_name = window.save_filename_lineedit.text()
                #     file_path = window.image_save_path
                #     with open(file_path + '/' + file_name + '.jpeg', 'wb') as file:
                #         file.write(bundle.args)
                if window.calibration_ck_box.isChecked() == False:
                    show_image(window.rear_camera_view, bundle.args)
            elif cam_id == 1:
                if window.calibration_ck_box.isChecked() == True:
                    pil_img = Image.open(io.BytesIO(bundle.args))
                    cv_img = np.array(pil_img)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
                    cross_pattern = cv_img.copy()
                    cross_pattern = cv2.line(cross_pattern, (0,720), (1920,720), (0,255,0),3,cv2.LINE_AA)
                    cross_pattern = cv2.line(cross_pattern, (960,0), (960,1440), (0,255,0),3,cv2.LINE_AA)
                    cross_grid_img = cross_pattern
                    data = cv2.imencode('.JPEG', cross_grid_img)[1].tobytes()
                    show_image(window.front_camera_view, data)
                # if window.save_mode_ck_box.isChecked() == True:
                #     file_name = window.save_filename_lineedit.text()
                #     file_path = window.image_save_path
                #     with open(file_path + os.path.sep + file_name + '.jpeg', 'wb') as file:
                #         file.write(bundle.args)
                if window.calibration_ck_box.isChecked() == False:
                    show_image(window.front_camera_view, bundle.args)
                
            else:
                is_valid = False

            if is_valid:
                window.front_camera_capture_button.setEnabled(True)
                window.rear_camera_capture_button.setEnabled(True)
                window.set_image(bundle.args)
                img = Image.open(io.BytesIO(bundle.args))
                img = np.array(img)
                #window.processing_button.clicked.connect(window.process_image(img, bg))
                
        elif bundle.request == ERequest.CAMERA_TOGGLE_TORCH:
            print('Toggle OK')
            window.torch_toggle_button.setEnabled(True)
        elif bundle.request == ERequest.DISPLAY_TAKE_PICTURE:
            if window.calibration_ck_box.isChecked() == True:
                    pil_img = Image.open(io.BytesIO(bundle.args))
                    cv_img = np.array(pil_img)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
                    cross_pattern = cv_img.copy()
                    cross_pattern = cv2.line(cross_pattern, (0,960), (1920,960), (0,255,0),3,cv2.LINE_AA)
                    cross_pattern = cv2.line(cross_pattern, (960,0), (960,1920), (0,255,0),3,cv2.LINE_AA)
                    cross_grid_img = cross_pattern
                    data = cv2.imencode('.JPEG', cross_grid_img)[1].tobytes()
                    show_image(window.display_camera_view, data)
            # if window.save_mode_ck_box.isChecked() == True:
            #     file_name = window.save_filename_lineedit.text()
            #     file_path = window.image_save_path
            #     with open(file_path + '/' + file_name + '.jpeg', 'wb') as file:
            #         file.write(bundle.args)
                # pil_img = Image.open(io.BytesIO(bundle.args)
                # pil_img.save(file_path + '/' + file_name + '.jpeg', 'jpeg')
            if window.calibration_ck_box.isChecked() == False:
                show_image(window.display_camera_view, bundle.args)
            window.set_image(bundle.args)

            img = Image.open(io.BytesIO(bundle.args))
            img = np.array(img)
            #window.set_image(img)
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

    
    def set_image(self, image):
        self.last_image = image
        return 

    # def process_image(self, image: np.array, bg) -> Any:
    #     print('processing')
    #     #self.last_image_bg = (image, bg)

    #     window: MainWindow = MainWindow.instance
    #     if window is None:
    #         return
        
    #     clf = image_clf(image)
    #     if bg == 'white':
    #         result1 = clf.processing_whitebg()
    #         print('end')     
    #         window.mmg_output_label.setText(str(result1[0][0]))
    #         window.msg_output_label.setText(str(result1[0][1]))
    #         window.smg_output_label.setText(str(result1[0][2]))
    #         window.ssg_output_label.setText(str(result1[0][3]))
    #         window.curve_a_output_label.setText(str(result1[2][0]))
    #         window.curve_b_output_label.setText(str(result1[2][1]))
    #         window.curve_c_output_label.setText(str(result1[2][2]))
    #         window.std_range_output_label.setText(str(result1[2][3]))
    #         window.gradient_output_label.setText(str(result1[2][4]))
    #         window.particle_sum_output_label.setText(str(result1[1]))
            
    #         return result1
        
    #     elif bg == 'check':
    #         result2 = clf.processing_checkpat()
    #         print('end')     
    #         window.supp_ratio_output_label.setText(str(result2))
    #         return result2
    
    # def show_image(self, view: QLabel, data: bytes):
    #     if self.calibration_ck_box.isChecked() == True:
    #         data_io = io.BytesIO(data)
    #         cv_img = np.array(data_io)
    #         print(cv_img.shape())
    #     pixmap = QPixmap()
    #     if pixmap.loadFromData(data, 'JPEG'):
    #         if pixmap.width() > pixmap.height():
    #             pixmap = pixmap.scaledToWidth(view.width())
    #         elif pixmap.width() < pixmap.height():
    #             pixmap = pixmap.scaledToHeight(view.height())

    #         view.setPixmap(pixmap)
    #     else:
    #         raise ValueError('Failed to load image.')
