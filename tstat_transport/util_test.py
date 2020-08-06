import unittest
from tstat_transport.common import (
    ConfigurationCapsule
)
import argparse

from tstat_transport.util import  _log

from tstat_transport.parse import TstatParse


class TestUtil(unittest.TestCase):

    def test_logger(self):
        _log("foobar", "hello world")


if __name__ == '__main__':
    unittest.main()
