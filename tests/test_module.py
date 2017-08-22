from unittest import TestCase
try:
    from unittest.mock import patch # pylint:disable=import-error,no-name-in-module
except ImportError:
    from mock import patch

from tempfile import mkstemp
from os import remove, write, close
from types import ModuleType

from backtest.module import ModuleLoader


class TestModuleLoader(TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.modulePath = mkstemp(suffix='.py')
        write(fd, 'test = lambda: testenv + 1')
        close(fd)

    @classmethod
    def tearDownClass(cls):
        remove(cls.modulePath)
        remove(cls.modulePath + 'c')

    def testGetName(self):
        name = 'test/modules/t e_s-t.0.py'
        loader = ModuleLoader()
        self.assertEqual(loader.get_module_name(name), 'test0')
        loader = ModuleLoader(prefix='p_')
        self.assertEqual(loader.get_module_name(name), 'p_test0')

    @patch('backtest.module.ModuleLoader.get_module_name', return_value='test')
    def testLoad(self, get_module_name):
        loader = ModuleLoader()
        module = loader.load(self.modulePath)
        self.assertIsInstance(module, ModuleType)
        self.assertEqual(module.__name__, 'test')
        get_module_name.assert_called_with(self.modulePath)

    @patch('backtest.module.ModuleLoader.get_module_name')
    def testLoadName(self, get_module_name):
        prefix = 'test_'
        name = 'testLoadName'
        loader = ModuleLoader(prefix=prefix)
        module = loader.load(self.modulePath, name=name)
        self.assertIsInstance(module, ModuleType)
        self.assertEqual(module.__name__, prefix + name)
        self.assertFalse(get_module_name.called)

    def testNameReload(self):
        name = 'testReload'
        name2 = 'testReload2'
        loader = ModuleLoader()
        module = loader.load(self.modulePath, name=name)
        module2 = loader.load(self.modulePath, name=name2)
        self.assertIsNot(module, module2)

    def testIgnoreReload(self):
        loader = ModuleLoader(on_reload=ModuleLoader.IGNORE)
        module = loader.load(self.modulePath)
        module2 = loader.load(self.modulePath)
        self.assertIs(module, module2)

    def testFailReload(self):
        name = 'testFailReload'
        loader = ModuleLoader(on_reload=ModuleLoader.FAIL)
        loader.load(self.modulePath, name=name)
        with self.assertRaises(ValueError):
            loader.load(self.modulePath, name=name)

    def testEnv(self):
        name = 'testEnv'
        loader = ModuleLoader()
        module = loader.load(self.modulePath, name=name, env={'testenv': 2})
        self.assertEqual(module.test(), 3)
