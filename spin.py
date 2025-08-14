#hace una animacion en la terminal mientras corre otro programa
#me sirve para saber que las cosas estan andando cuando tarda un rato
from itertools import cycle
from threading import Thread, Event
from time import sleep

class Spinner:
    def __init__(self, message='Conectandose '):
        self._stop_event = Event()
        self._sequence = cycle(['|', '\\', '-', '/'])
        self._message = message
        self._thread = Thread(target=self._spin, daemon=True)

    def _spin(self):
        while not self._stop_event.is_set():
            print(f'\r{self._message} {next(self._sequence)}', end='', flush=True)
            sleep(0.15)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()
