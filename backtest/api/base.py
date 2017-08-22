from os.path import basename, splitext

from ..module import ModuleLoader
from ..util import Namespace # pylint: disable=unused-import


class APIError(RuntimeError):
    pass


class Stop(Exception):
    pass


class API(object):
    def __init__(self, verbose=False):
        self.started = False
        self.state = None
        self.verbose = verbose

    def start(self):
        if not self.started:
            try:
                self.do_start()
                self.started = True
            except Stop:
                pass

    def tick(self, tick):
        if self.started:
            try:
                self.state = self.do_tick(tick)
            except Stop:
                self.stop()
        return self.state

    def stop(self):
        if self.started:
            try:
                self.do_stop()
            except Stop:
                pass
            self.started = False

    def do_start(self):
        raise NotImplementedError()

    def do_tick(self, tick):
        raise NotImplementedError()

    def do_stop(self):
        raise NotImplementedError()

    def get_plots(self): # pylint: disable=no-self-use
        return []


class PythonAPI(API):
    LOADER = ModuleLoader(prefix='strategy_', on_reload=ModuleLoader.FAIL)

    def __init__(self, module_path, verbose=False):
        super(PythonAPI, self).__init__(verbose)
        self.module = None
        self.module_path = module_path

    def __str__(self):
        return splitext(basename(self.module_path))[0]

    def do_start(self):
        if self.module is None:
            self.module = self.LOADER.load(self.module_path, env=self.get_env())

    def get_env(self):
        raise NotImplementedError()
