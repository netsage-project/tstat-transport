import unittest
from tstat_transport.common import (
    ConfigurationCapsule
)
import argparse, os

from tstat_transport.util import  _log

CONFIG='compose/tstat-transport/docker_config.ini'
OPTIONS_CONFIG = 'test_data/test_config.ini'


class TestConfigurationMethods(unittest.TestCase):

    # Note expects $RABBIT_HOST to be set
    def test_config_env_load(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        ## check int
        value = config_capsule.get_cfg_val('host')
        self.assertEqual(value, 'google.com')

    def test_config_load(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        value = config_capsule.get_cfg_val('routing_key')
        self.assertEqual(value, 'netsage_tstat')
        ## check int
        value = config_capsule.get_cfg_val('port', as_int=True)
        self.assertEqual(value, 5672)
        ## check bool
        value = config_capsule.get_cfg_val('use_ssl', as_bool=True)
        self.assertEqual(value, False)

    def test_rabbit_opts(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, OPTIONS_CONFIG)
        rabbit = config_capsule.get_rabbit_queue_opts()
        self.assertTrue('durable' in rabbit)
        self.assertEqual(rabbit.get('durable'), 'True')

    def test_ssl_opts(self):
        ns = argparse.Namespace(verbose=False, transport='rabbit')
        config_capsule = ConfigurationCapsule(ns, _log, OPTIONS_CONFIG)
        ssl = config_capsule.get_ssl_opts()
        self.assertTrue('server_side' in ssl)
        self.assertEqual(ssl.get('server_side'), '')


if __name__ == '__main__':
    unittest.main()
