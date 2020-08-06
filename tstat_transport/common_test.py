import unittest
from tstat_transport.common import (
    ConfigurationCapsule
)
import argparse

from tstat_transport.util import  _log

CONFIG='../test_config.ini'

class TestConfigurationMethods(unittest.TestCase):

    def test_config_load(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        value = config_capsule.get_cfg_val('routing_key')
        self.assertEqual(value, 'netsage_tstat')
        ## check int
        value = config_capsule.get_cfg_val('port', as_int=True)
        self.assertEqual(value, 5671)
        ## check bool
        value = config_capsule.get_cfg_val('use_ssl', as_bool=True)
        self.assertEqual(value, True)

    def test_rabbit_opts(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        rabbit = config_capsule.get_rabbit_queue_opts()
        self.assertTrue('durable' in rabbit)
        self.assertEqual(rabbit.get('durable'), 'True')

    def test_ssl_opts(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        ssl = config_capsule.get_ssl_opts()
        self.assertTrue('server_side' in ssl)
        self.assertEqual(ssl.get('server_side'), 'True')


if __name__ == '__main__':
    unittest.main()
