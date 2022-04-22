import socket
from threading import Thread

from interaction.protocol import Interactor
from interaction.bundle import Bundle
from interaction.byte_enum import ERequest, EResponse

i = 0


def digest_response(bundle: Bundle) -> None:
    """
    Handles response for host request.
    :param bundle: The bundle instance for the request.
    :return: None
    """
    global i
    print(f'ClientResp: {bundle}')
    if bundle.request == ERequest.CAMERA_TAKE_PICTURE:
        with open(f'{i}.jpeg', 'wb+') as file:
            file.write(bundle.args)
        print(f'File saved: {i}.jpeg')
        i += 1
    elif bundle.request == ERequest.CAMERA_TOGGLE_TORCH:
        print('Toggle OK')
    elif bundle.request == ERequest.DISPLAY_TAKE_PICTURE:
        with open(f'{i}.jpeg', 'wb+') as file:
            file.write(bundle.args)
        print(f'File saved: {i}.jpeg')
        i += 1
    elif bundle.request == ERequest.DISPLAY_SHOW_PICTURE:
        print('Display OK')
    else:
        print('Unknown')
    print()


def handle_client_request(bundle: Bundle) -> Bundle:
    """
    Handles request from camera client.
    :param bundle: The bundle for the request.
    :return: Response flag for the request.
    """
    if bundle.request == ERequest.ANY_QUIT:
        bundle.response = EResponse.ACK
    else:
        bundle.response = EResponse.REJECT

    print(f'ClientReq: {bundle}')
    return bundle


class MainConsole(Thread):
    PORT = 58431

    def __init__(self):
        super(MainConsole, self).__init__()

        self.camera_handler: Interactor = None
        self.display_handler: Interactor = None
        self.request_id = 0

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', MainConsole.PORT))
        self.server.listen(10)

    def run(self) -> None:
        # start socket thread
        Thread(target=MainConsole.listen, args=(self,)).start()

        while True:
            line = input().split(' ')

            self.request_id += 1
            if self.request_id > Interactor.MAX_REQ_ID:
                self.request_id = 0

            bundle: Bundle = Bundle(self.request_id, ERequest.NONE)
            if len(line) > 0:
                if line[0] == 'cmd':
                    if len(line) > 1:
                        if line[1] == '-c':
                            if line[2] == 'camera':
                                if len(line) > 3:
                                    bundle.request = ERequest.CAMERA_TAKE_PICTURE
                                    bundle.args = bytes([int(line[3])])
                                else:
                                    print('cmd -c camera [cam_id]')
                            elif line[2] == 'display':
                                bundle.request = ERequest.DISPLAY_TAKE_PICTURE
                            else:
                                print('cmd -c [camera or display]')
                        elif line[1] == '-t':
                            bundle.request = ERequest.CAMERA_TOGGLE_TORCH
                        elif line[1] == '-d':
                            if len(line) < 3:
                                print('cmd -d [filename]')
                            else:
                                path = str.join(' ', line[2:])
                                with open(path, 'rb+') as file:
                                    bundle.args = file.read()
                                bundle.request = ERequest.DISPLAY_SHOW_PICTURE
                        else:
                            print('cmd [-c(capture) or -t(torch) or -d(display)]')
                    else:
                        print('cmd [-c(capture) or -t(torch) or -d(display)]')
                elif line[0] == 'quit':
                    bundle.request = ERequest.ANY_QUIT
                else:
                    print('unknown command')

            if bundle.request != ERequest.NONE:
                if bundle.request.is_for_camera():
                    if self.camera_handler is None:
                        print('There is no camera')
                    else:
                        self.camera_handler.request(bundle)
                elif bundle.request.is_for_display():
                    if self.display_handler is None:
                        print('There is no display')
                    else:
                        self.display_handler.request(bundle)
                elif bundle.request.is_for_any():
                    if self.camera_handler is not None:
                        self.camera_handler.request(bundle)
                        self.camera_handler = None
                    if self.display_handler is not None:
                        self.display_handler.request(bundle)
                        self.display_handler = None

    def listen(self):
        print('Listen: Start listening')
        while True:
            # accept client to evaluate
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
                        print('Camera disconnected')

                    self.camera_handler = Interactor(client,
                                                     handle_client_request,
                                                     digest_response,
                                                     on_disconnected)
                    self.camera_handler.start()
                    bundle.response = EResponse.OK
            elif role == ERequest.DISPLAY:
                if self.display_handler is not None:
                    print(f'Listen: display, error')
                    bundle.response = EResponse.ERROR
                else:
                    print(f'Listen: display, ok')

                    def on_disconnected():
                        self.display_handler = None
                        print('Display disconnected')

                    self.display_handler = Interactor(client,
                                                      handle_client_request,
                                                      digest_response,
                                                      on_disconnected)
                    self.display_handler.start()
                    bundle.response = EResponse.OK
            else:
                print(f'Listen: unknown')
                bundle.response = EResponse.ERROR

            handle_client_request(bundle)
