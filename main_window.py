from PyQt6 import uic


class MainWindow:
    def __init__(self):
        form_class, window_class = uic.loadUiType("MainWindow.ui")
        self.window = window_class()
        self.form = form_class()
        self.form.setupUi(self.window)

    def show(self):
        self.window.show()
