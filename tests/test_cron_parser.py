import pytest

from kroner import parse_cron
from kroner import Cron

class TestCronParser:
  def test_example(self):
    assert(isinstance(parse_cron('* * * * *'), Cron))