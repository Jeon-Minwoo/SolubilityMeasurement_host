# import sys
# from PyQt6.QtWidgets import QApplication
# from main_window import MainWindow
#
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     win = MainWindow()
#     win.show()
#     sys.exit(app.exec())

import socket



def accept(client) -> socket:


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    client1 = server.accept()
    client2 = server.accept()
