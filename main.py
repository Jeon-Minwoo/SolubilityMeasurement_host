import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow
from main_console import MainConsole

if __name__ == '__main__':
    print('W(indow) / C(onsole) / Q(uit)')
    mode = '-'
    while mode in 'wcq':
        print('>> ', end='')
        mode = input()[0].lower()

    if mode != 'q':
        app = QApplication(sys.argv)
        if mode == 'w':
            win = MainWindow()
            win.show()
        elif mode == 'c':
            console = MainConsole()
            console.start()
        sys.exit(app.exec())
