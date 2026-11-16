from bisect import bisect_left, bisect_right
from calendar import monthrange
from collections.abc import Iterator, Sequence
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lark import Tree

from .parser import parse

MONTH_NAMES = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
WEEK_DAY_NAMES = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
FIRST_YEAR, LAST_YEAR = 1970, 2099
ONE_SECOND = timedelta(seconds=1)


class _Field:
  def __init__(self, values, specials=(), restricted=True):
    self.values = sorted(set(values))
    self.lookup = frozenset(self.values)
    # Day rules that depend on the month, as (text, kind, arg, arg)
    self.specials = list(specials)
    # False when the field is "*" or "?", used to combine days of month and week
    self.restricted = restricted


def _month_number(token) -> int:
  return int(token) if token.isdigit() else MONTH_NAMES.index(token.lower()) + 1


def _week_day_number(token) -> int:
  return int(token) if token.isdigit() else WEEK_DAY_NAMES.index(token.lower())


def _cron_weekday(day: date) -> int:
  # Python counts from Monday, cron from Sunday
  return (day.weekday() + 1) % 7


def _nearest_weekday(year: int, month: int, day: int) -> int:
  last = monthrange(year, month)[1]
  weekday = date(year, month, day).weekday()
  if weekday == 5:
    return day - 1 if day > 1 else day + 2
  if weekday == 6:
    return day + 1 if day < last else day - 2
  return day


def _month_day_special(item):
  args = [str(child) for child in item.children]
  if item.data == 'last_day':
    offset = int(args[1]) if len(args) > 1 else 0
    return ('L-%d' % offset if offset else 'L', 'last_day', offset, None)
  if item.data == 'nearest_weekday':
    return ('%dW' % int(args[0]), 'nearest_weekday', int(args[0]), None)
  return ('LW', 'last_weekday', None, None)


def _week_day_special(item):
  week_day = _week_day_number(item.children[0]) % 7
  if item.data == 'last_week_day':
    return ('%dL' % week_day, 'last_week_day', week_day, None)
  nth = int(item.children[1])
  return ('%d#%d' % (week_day, nth), 'nth_week_day', week_day, nth)


def _special_matches(special, day: date) -> bool:
  _, kind, arg, nth = special
  last = monthrange(day.year, day.month)[1]
  if kind == 'last_day':
    return day.day == max(1, last - arg)
  if kind == 'nearest_weekday':
    return day.day == _nearest_weekday(day.year, day.month, min(arg, last))
  if kind == 'last_weekday':
    return day.day == _nearest_weekday(day.year, day.month, last)
  if kind == 'last_week_day':
    return _cron_weekday(day) == arg and day.day + 7 > last
  return _cron_weekday(day) == arg and (day.day - 1) // 7 + 1 == nth


def _expand(item, low: int, high: int, number) -> range:
  args, step = item.children, None
  if args and isinstance(args[-1], Tree) and args[-1].data == 'step':
    args, step = args[:-1], int(args[-1].children[0])

  if item.data == 'any':
    start, end = low, high
  elif item.data == 'value':
    start = number(args[0])
    end = start if step is None else max(start, high)
  else:
    start, end = number(args[0]), number(args[1])
    if start > end:
      raise ValueError('Invalid range %s-%s' % (args[0], args[1]))
  return range(start, end + 1, step or 1)


def _parse_field(tree, low: int, high: int, number=int, special=None, modulo=None) -> _Field:
  items = tree.children
  if not isinstance(items[0], Tree):
    # "?" means no specific value
    return _Field(range(low, high + 1), restricted=False)

  values, specials = [], []
  for item in items:
    if item.data in ('any', 'value', 'range'):
      values.extend(_expand(item, low, high, number))
    else:
      specials.append(special(item))
  if modulo:
    values = [value % modulo for value in values]

  restricted = not (len(items) == 1 and items[0].data == 'any' and len(items[0].children) == 1)
  return _Field(values, specials, restricted)


def _ceil(values, value):
  index = bisect_left(values, value)
  return values[index] if index < len(values) else None


def _floor(values, value):
  index = bisect_right(values, value)
  return values[index - 1] if index else None


def _localize(moment: datetime, zone) -> datetime:
  if zone is None:
    return moment
  if moment.tzinfo is None:
    return moment.replace(tzinfo=zone)
  return moment.astimezone(zone)


def _wall(moment: datetime) -> datetime:
  return moment.replace(tzinfo=None, microsecond=0, fold=0)


def _key(moment: datetime):
  # Aware datetimes sharing a tzinfo compare by wall time, so compare instants instead
  return moment.timestamp() if moment.tzinfo else moment


def _exists(wall: datetime, zone) -> bool:
  # Wall times skipped by a DST change don't survive a round trip through UTC
  moment = wall.replace(tzinfo=zone)
  return moment.astimezone(dt_timezone.utc).astimezone(zone).replace(tzinfo=None) == wall


class Cron(Sequence):
  """A parsed cron expression.

  Accepts 5 fields (minutes to days of week), 6 fields (with leading seconds)
  or 7 fields (with seconds and trailing years). As a sequence it holds the
  expanded seconds, minutes, hours, days of month, months, days of week and years.
  """

  def __init__(self, line: str, tz_name: Optional[str] = None):
    self._line = line
    fields = {field.data: field for field in parse(line).children}

    self._seconds = _parse_field(fields['seconds'], 0, 59) if 'seconds' in fields else _Field([0])
    self._minutes = _parse_field(fields['minutes'], 0, 59)
    self._hours = _parse_field(fields['hours'], 0, 23)
    self._days_of_month = _parse_field(fields['days_of_month'], 1, 31, special=_month_day_special)
    self._months = _parse_field(fields['months'], 1, 12, _month_number)
    self._days_of_week = _parse_field(fields['days_of_week'], 0, 6, _week_day_number, _week_day_special, modulo=7)
    if 'years' in fields:
      self._years = _parse_field(fields['years'], FIRST_YEAR, LAST_YEAR)
    else:
      self._years = _Field(range(FIRST_YEAR, LAST_YEAR + 1))

    self._tz: Optional[ZoneInfo] = None
    if tz_name is not None:
      self.tz_name(tz_name)

  def __str__(self):
    return self._line

  def __repr__(self):
    if self._tz:
      return 'Cron(%r, tz_name=%r)' % (self._line, self.tz_name())
    return 'Cron(%r)' % self._line

  def __getitem__(self, index):
    return [
      self.seconds(), self.minutes(), self.hours(), self.days_of_month(),
      self.months(), self.days_of_week(), self.years(),
    ][index]

  def __len__(self):
    return 7

  # Handle time
  def tz_name(self, value: Optional[str] = None) -> Optional[str]:
    """Return the time zone name, setting it first when a value is given."""
    if value is not None:
      try:
        self._tz = ZoneInfo(value)
      except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError('Unknown time zone %r' % value) from error
    return self._tz.key if self._tz else None

  def timezone(self) -> Optional[ZoneInfo]:
    return self._tz

  def next_time(self, now: Optional[datetime] = None) -> Optional[datetime]:
    """The first run strictly after now, or None when there are no more runs."""
    zone = self._zone(now)
    now = _localize(now or datetime.now(zone), zone)
    return self._find(_wall(now), now, zone, forward=True)

  def previous_time(self, now: Optional[datetime] = None) -> Optional[datetime]:
    """The last run strictly before now, or None when there are no earlier runs."""
    zone = self._zone(now)
    now = _localize(now or datetime.now(zone), zone)
    return self._find(_wall(now), now, zone, forward=False)

  def occurrences_between(self, start_at: datetime, end_at: datetime) -> Iterator[datetime]:
    """Yield every run with start_at <= run < end_at."""
    zone = self._zone(start_at)
    start_at, end_at = _localize(start_at, zone), _localize(end_at, zone)
    moment = self._find(_wall(start_at), start_at, zone, forward=True, inclusive=True)
    while moment is not None and _key(moment) < _key(end_at):
      yield moment
      moment = self._find(_wall(moment), moment, zone, forward=True)

  def count_occurrences(self, start_at: datetime, end_at: datetime) -> int:
    """Count the runs with start_at <= run < end_at."""
    zone = self._zone(start_at)
    start_at, end_at = _localize(start_at, zone), _localize(end_at, zone)
    per_day = len(self._hours.values) * len(self._minutes.values) * len(self._seconds.values)

    # Whole days are counted arithmetically, partial days and DST changes run by run
    total, day = 0, _wall(start_at).date()
    while day.year <= LAST_YEAR:
      day_start = _localize(datetime.combine(day, time()), zone)
      if _key(day_start) >= _key(end_at):
        break
      day_end = _localize(datetime.combine(day + timedelta(days=1), time()), zone)

      if self._matches_date(day):
        whole = _key(start_at) <= _key(day_start) and _key(day_end) <= _key(end_at)
        if whole and (zone is None or day_start.utcoffset() == day_end.utcoffset()):
          total += per_day
        else:
          runs = self.occurrences_between(max(start_at, day_start, key=_key), min(end_at, day_end, key=_key))
          total += sum(1 for _ in runs)
      day += timedelta(days=1)
    return total

  def count_occurrences_for_year(self, year: Optional[int] = None) -> int:
    year = year or datetime.now(self._tz).year
    start_at = _localize(datetime(year, 1, 1), self._tz)
    end_at = _localize(datetime(year + 1, 1, 1), self._tz)
    return self.count_occurrences(start_at, end_at)

  def count_occurrences_current_year(self) -> int:
    return self.count_occurrences_for_year()

  # Spellings from the original design, kept so existing callers keep working
  occurances_between = occurrences_between
  count_occurances = count_occurrences
  count_occurrances_for_year = count_occurrences_for_year
  count_occurreances_current_year = count_occurrences_current_year

  # Expanded fields
  def original(self) -> str:
    return self._line

  def seconds(self) -> list:
    return list(self._seconds.values)

  def minutes(self) -> list:
    return list(self._minutes.values)

  def hours(self) -> list:
    return list(self._hours.values)

  def days_of_month(self) -> list:
    """Day numbers, followed by month dependent rules such as "L" or "15W"."""
    return self._days_of_month.values + [special[0] for special in self._days_of_month.specials]

  def months(self) -> list:
    return list(self._months.values)

  def days_of_week(self) -> list:
    """Day numbers with Sunday as 0, followed by rules such as "5L" or "1#2"."""
    return self._days_of_week.values + [special[0] for special in self._days_of_week.specials]

  def years(self) -> list:
    return list(self._years.values)

  def _zone(self, moment: Optional[datetime]):
    return self._tz or (moment.tzinfo if moment else None)

  def _matches_date(self, day: date) -> bool:
    if day.year not in self._years.lookup or day.month not in self._months.lookup:
      return False
    dom, dow = self._days_of_month, self._days_of_week
    in_dom = day.day in dom.lookup or any(_special_matches(special, day) for special in dom.specials)
    in_dow = _cron_weekday(day) in dow.lookup or any(_special_matches(special, day) for special in dow.specials)
    # Like Vixie cron, a day matches either field when both are restricted
    if dom.restricted and dow.restricted:
      return in_dom or in_dow
    return in_dom and in_dow

  def _find(self, wall: datetime, bound: datetime, zone, forward: bool, inclusive: bool = False):
    search = self._search_forward if forward else self._search_backward
    while True:
      wall = search(wall)
      if wall is None:
        return None
      moment = _localize(wall, zone)
      if zone is None or _exists(wall, zone):
        if _key(moment) == _key(bound):
          if inclusive:
            return moment
        elif (_key(moment) > _key(bound)) == forward:
          return moment
      wall += ONE_SECOND if forward else -ONE_SECOND

  def _search_forward(self, wall: datetime) -> Optional[datetime]:
    while True:
      if wall.year not in self._years.lookup:
        year = _ceil(self._years.values, wall.year)
        if year is None:
          return None
        wall = datetime(year, 1, 1)
        continue
      if wall.month not in self._months.lookup:
        wall = datetime(wall.year + wall.month // 12, wall.month % 12 + 1, 1)
        continue
      if not self._matches_date(wall.date()):
        wall = datetime.combine(wall.date() + timedelta(days=1), time())
        continue

      hour = _ceil(self._hours.values, wall.hour)
      if hour is None:
        wall = datetime.combine(wall.date() + timedelta(days=1), time())
        continue
      if hour != wall.hour:
        wall = wall.replace(hour=hour, minute=0, second=0)

      minute = _ceil(self._minutes.values, wall.minute)
      if minute is None:
        wall = wall.replace(minute=0, second=0) + timedelta(hours=1)
        continue
      if minute != wall.minute:
        wall = wall.replace(minute=minute, second=0)

      second = _ceil(self._seconds.values, wall.second)
      if second is None:
        wall = wall.replace(second=0) + timedelta(minutes=1)
        continue
      return wall.replace(second=second)

  def _search_backward(self, wall: datetime) -> Optional[datetime]:
    while True:
      if wall.year not in self._years.lookup:
        year = _floor(self._years.values, wall.year)
        if year is None:
          return None
        wall = datetime(year, 12, 31, 23, 59, 59)
        continue
      if wall.month not in self._months.lookup:
        wall = datetime(wall.year, wall.month, 1) - ONE_SECOND
        continue
      if not self._matches_date(wall.date()):
        wall = datetime.combine(wall.date(), time()) - ONE_SECOND
        continue

      hour = _floor(self._hours.values, wall.hour)
      if hour is None:
        wall = datetime.combine(wall.date(), time()) - ONE_SECOND
        continue
      if hour != wall.hour:
        wall = wall.replace(hour=hour, minute=59, second=59)

      minute = _floor(self._minutes.values, wall.minute)
      if minute is None:
        wall = wall.replace(minute=0, second=0) - ONE_SECOND
        continue
      if minute != wall.minute:
        wall = wall.replace(minute=minute, second=59)

      second = _floor(self._seconds.values, wall.second)
      if second is None:
        wall = wall.replace(second=0) - ONE_SECOND
        continue
      return wall.replace(second=second)


def parse_cron(s: str, tz_name: Optional[str] = None) -> Optional[Cron]:
  """Parse a cron expression, returning None when it or the time zone is invalid."""
  try:
    return Cron(s, tz_name=tz_name)
  except ValueError:
    return None
