import threading


class InterruptableThread(threading.Thread):
    def __init__(self, target, args):
        super(InterruptableThread, self).__init__(target=target, args=args)
        self.error = InterruptedError()

    def interrupt(self):
        try:
            raise self.error
        except InterruptedError:
            print(f'{super(InterruptableThread, self).getName()} interrupted.')
