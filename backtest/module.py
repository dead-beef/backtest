import sys
from os.path import basename, splitext

try:
    from importlib.util import spec_from_file_location, module_from_spec # pylint:disable=import-error,no-name-in-module

    def _import(name, path):
        spec = spec_from_file_location(name, path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
except ImportError:
    try:
        from importlib.machinery import SourceFileLoader # pylint:disable=import-error,no-name-in-module

        def _import(name, path):
            return SourceFileLoader(name, path).load_module()
    except ImportError:
        import imp # pylint:disable=import-error,no-name-in-module

        def _import(name, path):
            return imp.load_source(name, path)

#def _reload(name, path):
#    raise NotImplementedError(
#        'reload: name="{0}" path="{1}"'.format(name, path)
#    )


class ModuleLoader(object):
    IGNORE = 0
    #RELOAD = 1
    FAIL = 2

    def __init__(self, prefix='', on_reload=IGNORE):
        self.on_reload = on_reload
        self.prefix = prefix

    def get_module_name(self, path):
        name = splitext(basename(path))[0]
        name = ''.join(c for c in name.lower() if c.isalnum())
        return self.prefix + name

    def _load(self, name, path):
        try:
            module = sys.modules[name]
        except KeyError:
            return _import(name, path)
        if self.on_reload == self.IGNORE:
            return module
        #if self.on_reload == self.RELOAD:
        #    return _reload(name, path)
        raise ValueError('reload: name="{0}" path="{1}"'.format(name, path))

    def load(self, path, name=None, env=None):
        if name is None:
            name = self.get_module_name(path)
        else:
            name = self.prefix + name

        module = self._load(name, path)

        if env is not None:
            for name, value in env.items():
                setattr(module, name, value)

        return module
