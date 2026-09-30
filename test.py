from lark import Lark
from pprint import pprint
from typing import Optional

from datetime import datetime
from collections.abc import Sequence


class Cron(Sequence):
  def __init__(self, line: str):
    pass

  def __str__(self):
    pass

  def __repr__(self):
    pass

  def __list__(self): ...

  # Handle time
  def tz_name(self, value: str = None):
    pass

  def next_time(now: datetime = None) -> datetime:
    pass

  def previous_time(now: datetime = None) -> datetime:
    pass

  # Iterator
  def occurances_between():

  def count_occurances(start_at: datetime, end_at: datetime) -> int:
    pass

  def count_occurrances_for_year() -> int
    pass

  def count_occurreances_current_year() -> int:
    pass

  def original(): ...
  def seconds(): ...
  def minutes(): ...
  def hours(): ...
  def months(): ...
  def years(): ...
  def days_of_month(): ...
  def days_of_week(): ...
  def timezone(): ...




  def is

GRAMMER = '''
  start: SECONDS WHITESPACE MINUTES WHITESPACE HOUR MONTH_DAY
  WHITESPACE: (" ")+

  SECONDS: (ASTERISK | CLOCK_DIGITS | CLOCK_RANGE | CLOCK_RANGE_SHORTCUT)
  MINUTES: (ASTERISK | CLOCK_DIGITS | CLOCK_RANGE | CLOCK_RANGE_SHORTCUT)
  HOUR: (ASTERISK | HOUR_DIGITS | HOUR_RANGE | HOUR_RANGE_SHORTCUT)
  MONTH_DAY: ASTERISK | LAST_DAY_OF_MONTH | WEEKEDAY | MONTH_DIGIT | MONTH_RANGE | MONTH_SHORT_RANGE

  LAST_DAY_OF_MONTH: "L"
  WEEKDAY: "W"
  MONTH_DIGIT: NUMBER | ("0".."2") NUMBER | "3" ("0" .. "1")
  MONTH_RANGE: MONTH_DIGIT "-" MONTH_DIGIT
  MONTH_SHORT_RANGE: MONTH_DIGIT "/" MONTH_DIGIT

  CLOCK_DIGITS: NUMBER | ("0".."6" NUMBER)
  CLOCK_RANGE: CLOCK_DIGITS "-" CLOCK_DIGITS
  CLOCK_RANGE_SHORTCUT: (ASTERISK | CLOCK_DIGITS) "/" CLOCK_DIGITS
  HOUR_DIGITS: NUMBER | ("0".."1" NUMBER)  | ("2" ("0".."3"))
  HOUR_RANGE: HOUR_DIGITS "-" HOUR_DIGITS
  HOUR_RANGE_SHORTCUT: (ASTERISK | HOUR_DIGITS) "/" HOUR_DIGITS
  NUMBER: "0".."9"

  ASTERISK: "*"
'''


lark = Lark(GRAMMER)

pprint(lark.parse("59 * 23"))
# pprint(lark.parse("*"))
# pprint(lark.parse("5-25"))
# pprint(lark.parse("*/15"))
