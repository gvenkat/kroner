from lark import Lark, Token, Tree
from lark.exceptions import LarkError

GRAMMAR = r"""
  // Seconds are optional: 5 fields, 6 fields with seconds, or 7 fields with seconds and years.
  start: seconds _WS minutes _WS hours _WS days_of_month _WS months _WS days_of_week (_WS years)?
       | minutes _WS hours _WS days_of_month _WS months _WS days_of_week

  // Each field is a comma separated list of items
  seconds: clock ("," clock)*
  minutes: clock ("," clock)*
  hours: hour ("," hour)*
  days_of_month: month_day ("," month_day)* | NO_SPECIFIC
  months: month ("," month)*
  days_of_week: week_day ("," week_day)* | NO_SPECIFIC
  years: year ("," year)*

  // An item is "*", a value or a range, with an optional "/step"
  ?clock: ANY step? -> any
        | CLOCK_DIGITS step? -> value
        | CLOCK_DIGITS "-" CLOCK_DIGITS step? -> range

  ?hour: ANY step? -> any
       | HOUR_DIGITS step? -> value
       | HOUR_DIGITS "-" HOUR_DIGITS step? -> range

  ?month_day: ANY step? -> any
            | MONTH_DAY_DIGITS step? -> value
            | MONTH_DAY_DIGITS "-" MONTH_DAY_DIGITS step? -> range
            | LAST_DAY ("-" MONTH_DAY_DIGITS)? -> last_day
            | MONTH_DAY_DIGITS NEAREST_WEEKDAY -> nearest_weekday
            | LAST_DAY NEAREST_WEEKDAY -> last_weekday

  ?month: ANY step? -> any
        | MONTH_VALUE step? -> value
        | MONTH_VALUE "-" MONTH_VALUE step? -> range

  ?week_day: ANY step? -> any
           | WEEK_DAY_VALUE step? -> value
           | WEEK_DAY_VALUE "-" WEEK_DAY_VALUE step? -> range
           | WEEK_DAY_VALUE LAST_DAY -> last_week_day
           | WEEK_DAY_VALUE "#" NTH -> nth_week_day

  ?year: ANY step? -> any
       | YEAR_DIGITS step? -> value
       | YEAR_DIGITS "-" YEAR_DIGITS step? -> range

  step: "/" STEP

  // Longer alternatives come first so the lexer doesn't stop at a shorter match
  CLOCK_DIGITS: /[0-5]\d|\d/
  HOUR_DIGITS: /2[0-3]|[01]\d|\d/
  MONTH_DAY_DIGITS: /3[01]|[12]\d|0?[1-9]/
  MONTH_DIGITS: /1[0-2]|0?[1-9]/
  WEEK_DAY_DIGITS: /[0-7]/
  YEAR_DIGITS: /19[7-9]\d|20\d\d/

  MONTH_NAME: /jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec/i
  WEEK_DAY_NAME: /sun|mon|tue|wed|thu|fri|sat/i

  MONTH_VALUE: MONTH_DIGITS | MONTH_NAME
  WEEK_DAY_VALUE: WEEK_DAY_DIGITS | WEEK_DAY_NAME

  STEP: /[1-9]\d*/
  NTH: /[1-5]/

  ANY: "*"
  NO_SPECIFIC: "?"
  LAST_DAY: "L"
  NEAREST_WEEKDAY: "W"

  _WS: /[ \t]+/
"""

_parser = Lark(GRAMMAR)


def parse(line: str) -> Tree[Token]:
    """Parse a cron expression into a syntax tree, raising ValueError when it is invalid."""
    try:
        return _parser.parse(line.strip())
    except LarkError as error:
        raise ValueError(f'Invalid cron expression {line!r}') from error
