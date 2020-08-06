import os
import unittest

import pytest

from tstat_transport.common import (
    ConfigurationCapsule
)
import argparse

from tstat_transport.util import log, _log

from tstat_transport.parse import TstatParse


class TestParserMethods(unittest.TestCase):
    def setUp(self):
        DONE_FILE = "test_data/parse_data.out/.processed"
        if os.path.exists("test_data/parse_data.out/.processed"):
            os.remove(DONE_FILE)

    def __load__config__(self, ssl=False):
        #CONFIG = '../test_data/test_config_ssl.ini'

        CONFIG = 'test_data/test_config.ini'
        if ssl:
            CONFIG = 'test_data/test_config_ssl.ini'

        ns = argparse.Namespace(verbose=False, transport='rabbit', directory='test_data', debug=False,
                                no_transport=False, sensor='SensorName', instance='instanceID',
                                threshold=0)
        config_capsule = ConfigurationCapsule(ns, _log, CONFIG)
        return config_capsule

    def test_parser(self):
        config = self.__load__config__()
        parser = TstatParse(config)

        for root, dirs, files in os.walk('test_data/parse_data.out'):
            parser.process_output(root, dirs, files)
        self.assertIsNotNone(parser)
        self.validate_file()
        count = self.get_queue_size(parser._transport, config)
        log.info("count is: {}".format(count))

        self.assertTrue(count > 0)
        ## Process again
        for root, dirs, files in os.walk('test_data/parse_data.out'):
            parser.process_output(root, dirs, files)
        next_count = self.get_queue_size(parser._transport, config)
        self.assertTrue(count, next_count)
        self.reset_queue(parser._transport, config)


    #Disabled, since by default rabbit has no SSL
    # def test_ssl_parser(self):
    #     config = self.__load__config__(ssl=True)
    #     parser = TstatParse(config)
    #
    #     for root, dirs, files in os.walk('test_data/parse_data.out'):
    #         parser.process_output(root, dirs, files)
    #     self.assertIsNotNone(parser)
    #     self.validate_rabbit(parser._transport, config)
    #     self.validate_file()
    #     self.reset_queue(parser._transport, config)

    def get_queue_size(self, transport, config):
        queue_name = config.get_cfg_val('queue')
        res = transport._channel.queue_declare(
            queue=queue_name, **config.get_rabbit_queue_opts())
        return res.method.message_count

    def reset_queue(self, transport, config):
        queue_name = config.get_cfg_val('queue')
        transport._channel.queue_delete(queue=queue_name)

    def validate_rabbit(self, transport, config, cleanup):
        ## Redeclare queue to get queue size
        queue_name = config.get_cfg_val('queue')
        res = transport._channel.queue_declare(
            queue=queue_name, **config.get_rabbit_queue_opts())
        ## Validate message count
        self.assertTrue(res.method.message_count > 0)
        if cleanup:
            transport._channel.queue_delete(queue=queue_name)

    def validate_file(self):
        self.assertTrue(os.path.exists("test_data/parse_data.out/.processed"), ".processed file has not been created")


if __name__ == '__main__':
    unittest.main()
