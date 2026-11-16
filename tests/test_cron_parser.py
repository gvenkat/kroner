from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from kroner import Cron, parse_cron

NEW_YORK = ZoneInfo('America/New_York')


class TestParsing:
  def test_example(self):
    assert isinstance(parse_cron('* * * * *'), Cron)

  def test_five_fields_default_seconds_and_years(self):
    cron = Cron('* * * * *')
    assert cron.seconds() == [0]
    assert cron.minutes() == list(range(60))
    assert cron.hours() == list(range(24))
    assert cron.days_of_month() == list(range(1, 32))
    assert cron.months() == list(range(1, 13))
    assert cron.days_of_week() == list(range(7))
    assert cron.years() == list(range(1970, 2100))

  def test_six_fields_have_seconds(self):
    cron = Cron('30 0 12 * * ?')
    assert cron.seconds() == [30]
    assert cron.minutes() == [0]
    assert cron.hours() == [12]

  def test_seven_fields_have_years(self):
    assert Cron('0 0 0 1 1 ? 2030-2032').years() == [2030, 2031, 2032]

  def test_steps_ranges_and_lists(self):
    cron = Cron('*/15 9-17/4 1,15,20-22 * *')
    assert cron.minutes() == [0, 15, 30, 45]
    assert cron.hours() == [9, 13, 17]
    assert cron.days_of_month() == [1, 15, 20, 21, 22]

  def test_value_with_step_runs_to_end_of_field(self):
    assert Cron('5/20 * * * *').minutes() == [5, 25, 45]

  def test_names_are_case_insensitive(self):
    cron = Cron('0 0 * jan,MAR,Dec mon-FRI')
    assert cron.months() == [1, 3, 12]
    assert cron.days_of_week() == [1, 2, 3, 4, 5]

  def test_sunday_can_be_seven(self):
    assert Cron('0 0 * * 7').days_of_week() == [0]
    assert Cron('0 0 * * 5-7').days_of_week() == [0, 5, 6]

  def test_special_day_rules(self):
    cron = Cron('0 0 L,15W * 5L,1#2')
    assert cron.days_of_month() == ['L', '15W']
    assert cron.days_of_week() == ['5L', '1#2']
    assert Cron('0 0 L-3,LW * ?').days_of_month() == ['L-3', 'LW']

  @pytest.mark.parametrize('line', [
    '',
    'hello',
    '* * * *',
    '* * * * * * * *',
    '60 * * * *',
    '* 24 * * *',
    '* * 0 * *',
    '* * 32 * *',
    '* * * 13 *',
    '* * * * 8',
    '5-1 * * * *',
    '* * * * FRI-MON',
    '0 0 * * 1#6',
    '*/0 * * * *',
    '0 0 0 1 1 ? 1969',
    '0 0 0 1 1 ? 2100',
  ])
  def test_invalid_expressions(self, line):
    assert parse_cron(line) is None
    with pytest.raises(ValueError):
      Cron(line)

  def test_invalid_time_zone(self):
    assert parse_cron('* * * * *', tz_name='Mars/Olympus') is None
    with pytest.raises(ValueError):
      Cron('* * * * *', tz_name='Mars/Olympus')

  def test_surrounding_whitespace_is_ignored(self):
    assert Cron('  0 0 * * *\n').minutes() == [0]


class TestSequence:
  def test_fields_as_sequence(self):
    cron = Cron('0 */15 9-17 * * MON-FRI')
    assert len(cron) == 7
    assert cron[0] == [0]
    assert cron[1] == [0, 15, 30, 45]
    assert cron[-1] == cron.years()
    assert cron[2:4] == [list(range(9, 18)), list(range(1, 32))]
    assert list(cron)[5] == [1, 2, 3, 4, 5]
    with pytest.raises(IndexError):
      cron[7]

  def test_str_and_repr(self):
    cron = Cron('0 0 * * *')
    assert str(cron) == '0 0 * * *'
    assert cron.original() == '0 0 * * *'
    assert repr(cron) == "Cron('0 0 * * *')"
    assert repr(Cron('0 0 * * *', tz_name='UTC')) == "Cron('0 0 * * *', tz_name='UTC')"

  def test_tz_name_get_and_set(self):
    cron = Cron('0 0 * * *')
    assert cron.tz_name() is None
    assert cron.timezone() is None
    assert cron.tz_name('Europe/Oslo') == 'Europe/Oslo'
    assert cron.timezone() == ZoneInfo('Europe/Oslo')


class TestNextAndPrevious:
  @pytest.mark.parametrize('now, expected', [
    (datetime(2026, 11, 13, 10, 7, 30), datetime(2026, 11, 13, 10, 15)),
    (datetime(2026, 11, 13, 10, 15), datetime(2026, 11, 13, 10, 30)),
    (datetime(2026, 11, 13, 10, 14, 59, 999999), datetime(2026, 11, 13, 10, 15)),
    (datetime(2026, 12, 31, 23, 50), datetime(2027, 1, 1)),
  ])
  def test_next_time(self, now, expected):
    assert Cron('*/15 * * * *').next_time(now) == expected

  @pytest.mark.parametrize('now, expected', [
    (datetime(2026, 11, 13, 10, 7, 30), datetime(2026, 11, 13, 10, 0)),
    (datetime(2026, 11, 13, 10, 15), datetime(2026, 11, 13, 10, 0)),
    (datetime(2026, 11, 13, 10, 15, 0, 500000), datetime(2026, 11, 13, 10, 15)),
    (datetime(2027, 1, 1, 0, 0), datetime(2026, 12, 31, 23, 45)),
  ])
  def test_previous_time(self, now, expected):
    assert Cron('*/15 * * * *').previous_time(now) == expected

  def test_seconds_field(self):
    cron = Cron('*/20 * * * * ?')
    assert cron.next_time(datetime(2026, 1, 1, 0, 0, 41)) == datetime(2026, 1, 1, 0, 1, 0)
    assert cron.previous_time(datetime(2026, 1, 1, 0, 0, 41)) == datetime(2026, 1, 1, 0, 0, 40)

  def test_leap_day(self):
    cron = Cron('0 0 29 2 *')
    assert cron.next_time(datetime(2026, 3, 1)) == datetime(2028, 2, 29)
    assert cron.previous_time(datetime(2026, 3, 1)) == datetime(2024, 2, 29)

  def test_runs_out_of_years(self):
    cron = Cron('0 0 0 1 1 ? 2030')
    assert cron.next_time(datetime(2029, 6, 1)) == datetime(2030, 1, 1)
    assert cron.next_time(datetime(2031, 1, 1)) is None
    assert cron.previous_time(datetime(2029, 1, 1)) is None
    assert Cron('* * * * *').next_time(datetime(2099, 12, 31, 23, 59)) is None

  def test_defaults_to_now(self):
    before = datetime.now()
    cron = Cron('* * * * * ?')
    assert cron.next_time() > before
    assert cron.previous_time() <= datetime.now()


class TestDayRules:
  @pytest.mark.parametrize('line, now, expected', [
    # Last day of the month, and three days before it
    ('0 0 L * ?', datetime(2026, 2, 10), datetime(2026, 2, 28)),
    ('0 0 L-2 * ?', datetime(2026, 2, 10), datetime(2026, 2, 26)),
    # Sunday 15 November 2026 moves to Monday the 16th
    ('0 0 15W * ?', datetime(2026, 11, 1), datetime(2026, 11, 16)),
    # Saturday 1 August 2026 moves forward to Monday the 3rd, not back into July
    ('0 0 1W * ?', datetime(2026, 7, 15), datetime(2026, 8, 3)),
    # Saturday 31 October 2026 moves back to Friday the 30th
    ('0 0 LW * ?', datetime(2026, 10, 1), datetime(2026, 10, 30)),
    # Last Friday and second Monday of November 2026
    ('0 0 ? * 5L', datetime(2026, 11, 1), datetime(2026, 11, 27)),
    ('0 0 ? * FRIL', datetime(2026, 11, 1), datetime(2026, 11, 27)),
    ('0 0 ? * 1#2', datetime(2026, 11, 1), datetime(2026, 11, 9)),
    ('0 0 ? * MON#2', datetime(2026, 11, 1), datetime(2026, 11, 9)),
  ])
  def test_next_time(self, line, now, expected):
    assert Cron(line).next_time(now) == expected

  def test_restricted_days_of_month_and_week_match_either(self):
    # Friday 6 November comes before the 13th
    cron = Cron('0 0 13 * 5')
    assert cron.next_time(datetime(2026, 11, 1)) == datetime(2026, 11, 6)
    assert cron.next_time(datetime(2026, 11, 6)) == datetime(2026, 11, 13)

  def test_unrestricted_day_of_week_is_ignored(self):
    assert Cron('0 0 13 * *').next_time(datetime(2026, 11, 1)) == datetime(2026, 11, 13)
    assert Cron('0 0 * * 5').next_time(datetime(2026, 11, 1)) == datetime(2026, 11, 6)


class TestTimeZones:
  def test_naive_input_is_read_in_cron_zone(self):
    cron = Cron('0 9 * * *', tz_name='America/New_York')
    assert cron.next_time(datetime(2026, 11, 13, 8)) == datetime(2026, 11, 13, 9, tzinfo=NEW_YORK)

  def test_aware_input_is_converted_to_cron_zone(self):
    cron = Cron('0 9 * * *', tz_name='America/New_York')
    # 15:00 UTC is 10:00 in New York, so the next run is tomorrow
    result = cron.next_time(datetime(2026, 11, 13, 15, tzinfo=timezone.utc))
    assert result.tzinfo == NEW_YORK
    assert result == datetime(2026, 11, 14, 14, tzinfo=timezone.utc)

  def test_aware_input_without_cron_zone_keeps_its_zone(self):
    result = Cron('0 9 * * *').next_time(datetime(2026, 11, 13, 10, tzinfo=timezone.utc))
    assert result == datetime(2026, 11, 14, 9, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc

  def test_skipped_wall_time_is_skipped(self):
    # 2:30 doesn't exist in New York on 8 March 2026
    cron = Cron('30 2 * * *', tz_name='America/New_York')
    assert cron.next_time(datetime(2026, 3, 7, 3)) == datetime(2026, 3, 9, 2, 30, tzinfo=NEW_YORK)
    assert cron.previous_time(datetime(2026, 3, 9, 0)) == datetime(2026, 3, 7, 2, 30, tzinfo=NEW_YORK)

  def test_repeated_wall_time_runs_once(self):
    # 1:30 happens twice in New York on 1 November 2026
    cron = Cron('30 1 * * *', tz_name='America/New_York')
    first = cron.next_time(datetime(2026, 11, 1))
    # Ambiguous times never compare equal across zones (PEP 495), so compare instants
    assert first.timestamp() == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc).timestamp()
    assert cron.next_time(first) == datetime(2026, 11, 2, 1, 30, tzinfo=NEW_YORK)

  def test_runs_are_ordered_across_fall_back(self):
    cron = Cron('*/30 * * * *', tz_name='America/New_York')
    runs = list(cron.occurrences_between(datetime(2026, 11, 1, 0), datetime(2026, 11, 1, 3)))
    instants = [run.timestamp() for run in runs]
    assert instants == sorted(instants)
    assert len(runs) == 6


class TestOccurrences:
  def test_occurrences_between_includes_start_and_excludes_end(self):
    runs = list(Cron('0 0 * * *').occurrences_between(datetime(2026, 1, 1), datetime(2026, 1, 4)))
    assert runs == [datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3)]

  def test_occurrences_between_empty(self):
    assert list(Cron('0 0 * * *').occurrences_between(datetime(2026, 1, 1, 1), datetime(2026, 1, 1, 23))) == []

  def test_count_partial_days(self):
    cron = Cron('*/15 * * * *')
    assert cron.count_occurrences(datetime(2026, 1, 1, 10, 7), datetime(2026, 1, 2, 10, 7)) == 96

  def test_count_matches_occurrences_between(self):
    cron = Cron('0 */7 9-17 ? * MON,WED,5L')
    start_at, end_at = datetime(2026, 1, 3, 12, 30), datetime(2026, 3, 17, 11)
    assert cron.count_occurrences(start_at, end_at) == len(list(cron.occurrences_between(start_at, end_at)))

  def test_count_for_year(self):
    # 2026 has 261 weekdays, each with 9 hours of 4 runs
    assert Cron('0 */15 9-17 * * MON-FRI').count_occurrences_for_year(2026) == 261 * 36
    assert Cron('* * * * *').count_occurrences_for_year(2024) == 366 * 1440

  def test_count_for_year_across_dst(self):
    # New York loses an hour in March and repeats one, counted once, in November
    cron = Cron('* * * * *', tz_name='America/New_York')
    assert cron.count_occurrences_for_year(2026) == 365 * 1440 - 60
    assert cron.count_occurrences(datetime(2026, 3, 8), datetime(2026, 3, 9)) == 23 * 60
    assert cron.count_occurrences(datetime(2026, 11, 1), datetime(2026, 11, 2)) == 24 * 60

  def test_count_current_year(self):
    cron = Cron('0 0 1 * *')
    assert cron.count_occurrences_current_year() == 12

  def test_design_spellings_still_work(self):
    cron = Cron('0 0 1 * *')
    assert cron.count_occurrances_for_year(2026) == 12
    assert cron.count_occurreances_current_year() == 12
    assert cron.count_occurances(datetime(2026, 1, 1), datetime(2027, 1, 1)) == 12
    assert len(list(cron.occurances_between(datetime(2026, 1, 1), datetime(2027, 1, 1)))) == 12
