# kroner

Parse cron expressions and work out when they run, with time zone and daylight saving support.

```python
from datetime import datetime
from kroner import Cron

cron = Cron('0 */15 9-17 * * MON-FRI', tz_name='America/New_York')

cron.next_time(datetime(2026, 11, 16, 10, 7))      # 2026-11-16 10:15:00-05:00
cron.previous_time(datetime(2026, 11, 16, 10, 7))  # 2026-11-16 10:00:00-05:00
cron.count_occurrences_for_year(2026)              # 9396
```

Requires Python 3.10 or later. The only dependency is [lark](https://github.com/lark-parser/lark).

## Installation

From a checkout of this repository:

```sh
uv sync            # or: pip install .
```

## Expression syntax

An expression has 5, 6 or 7 space-separated fields:

| Fields | Layout |
| --- | --- |
| 5 | `minute hour day-of-month month day-of-week` |
| 6 | `second minute hour day-of-month month day-of-week` |
| 7 | `second minute hour day-of-month month day-of-week year` |

With 5 fields, runs happen at second 0. Without a year field, any year from 1970 to 2099 matches.

| Field | Values | Names |
| --- | --- | --- |
| second | 0–59 | |
| minute | 0–59 | |
| hour | 0–23 | |
| day of month | 1–31 | |
| month | 1–12 | `JAN`–`DEC` |
| day of week | 0–7 (0 and 7 are Sunday) | `SUN`–`SAT` |
| year | 1970–2099 | |

Names are case-insensitive.

### Operators

| Syntax | Meaning | Example |
| --- | --- | --- |
| `*` | every value | `* * * * *` runs every minute |
| `a,b` | list | `0 9,17 * * *` runs at 9:00 and 17:00 |
| `a-b` | range, inclusive | `0 9 * * MON-FRI` runs on weekdays |
| `*/n` | every *n*th value | `*/15 * * * *` runs every 15 minutes |
| `a-b/n` | every *n*th value in a range | `0 9-17/4 * * *` runs at 9, 13 and 17 |
| `a/n` | every *n*th value from *a* to the end | `5/20 * * * *` runs at :05, :25 and :45 |
| `?` | no specific value (day fields only) | `0 0 12 1 * ?` |

### Day rules

These depend on the month and are only allowed in the day fields.

| Field | Syntax | Meaning |
| --- | --- | --- |
| day of month | `L` | last day of the month |
| day of month | `L-n` | *n* days before the last day |
| day of month | `nW` | weekday nearest day *n*, without crossing into another month |
| day of month | `LW` | last weekday of the month |
| day of week | `nL` | last day *n* of the month, e.g. `5L` or `FRIL` is the last Friday |
| day of week | `n#k` | the *k*th day *n* of the month, e.g. `1#2` or `MON#2` is the second Monday |

### Day of month and day of week together

As in Vixie cron, when both day fields are restricted a day matches if **either** one does: `0 0 13 * 5` runs on the 13th and on every Friday. If one of them is `*` or `?`, only the other one counts.

### Shorthands

| Shorthand | Same as |
| --- | --- |
| `@yearly`, `@annually` | `0 0 1 1 *` |
| `@monthly` | `0 0 1 * *` |
| `@weekly` | `0 0 * * 0` |
| `@daily`, `@midnight` | `0 0 * * *` |
| `@hourly` | `0 * * * *` |

The full mapping is exported as `kroner.MACROS`.

## API

### Parsing

```python
from kroner import Cron, parse_cron

Cron('*/5 * * * *')                    # raises ValueError if the expression is invalid
Cron('@daily', tz_name='Europe/Oslo')  # ValueError for an unknown time zone too
parse_cron('not a cron')               # returns None instead of raising
```

### Finding runs

All of these take `datetime` values. Results are in the cron's time zone if it has one. Otherwise they keep the zone of the input, or are naive if the input is naive.

| Method | Returns |
| --- | --- |
| `next_time(now=None)` | the first run strictly after `now` (default: the current time), or `None` if there are no more |
| `previous_time(now=None)` | the last run strictly before `now`, or `None` |
| `occurrences_between(start_at, end_at)` | an iterator over runs with `start_at <= run < end_at` |
| `count_occurrences(start_at, end_at)` | the number of runs in the same range, counted without listing each one |
| `count_occurrences_for_year(year=None)` | the number of runs in a calendar year (default: the current year) |
| `count_occurrences_current_year()` | the number of runs in the current year |

```python
cron = Cron('0 */15 9-17 * * MON-FRI', tz_name='America/New_York')
list(cron.occurrences_between(datetime(2026, 11, 16, 9), datetime(2026, 11, 16, 10)))
# [09:00, 09:15, 09:30, 09:45] on 2026-11-16, all -05:00
```

The earlier spellings `occurances_between`, `count_occurances`, `count_occurrances_for_year` and `count_occurreances_current_year` still work as aliases.

### Inspecting an expression

| Method | Returns |
| --- | --- |
| `seconds()`, `minutes()`, `hours()`, `months()`, `years()` | sorted lists of the values that match |
| `days_of_month()` | matching day numbers, then any day rules as text, e.g. `['L', '15W']` |
| `days_of_week()` | matching day numbers with Sunday as 0, then any day rules, e.g. `['5L', '1#2']` |
| `original()`, `str(cron)` | the expression exactly as given |
| `expression()` | the expression with any shorthand expanded, e.g. `'0 0 * * *'` for `@daily` |
| `tz_name(value=None)` | the time zone name, setting it first if `value` is given |
| `timezone()` | the `zoneinfo.ZoneInfo`, or `None` |

A `Cron` is also a sequence of its seven expanded fields, in the order seconds, minutes, hours, days of month, months, days of week, years:

```python
cron = Cron('0 */15 9-17 * * MON-FRI')
cron[1]        # [0, 15, 30, 45]
list(cron)[5]  # [1, 2, 3, 4, 5]
len(cron)      # 7
```

### Time zones and daylight saving

- A naive `datetime` passed to a cron with a time zone is read as a time in that zone. An aware one is converted to it.
- When clocks go forward, wall times that don't exist that day are skipped. For example, `30 2 * * *` in New York doesn't run on 8 March 2026.
- When clocks go back, a wall time that happens twice runs only once, the first time.

## Development

### Code style

Formatting and linting are handled by [Ruff](https://docs.astral.sh/ruff/) and type checking by [mypy](https://mypy.readthedocs.io/) in strict mode, both configured in `pyproject.toml`.

```sh
uv run ruff format          # format
uv run ruff check --fix     # lint and auto-fix
uv run mypy                 # type check src/ and tests/
uv run pytest               # test
```

- **Formatting:** 4-space indentation, single quotes, 100-character lines. Let `ruff format` decide; don't hand-format.
- **Imports:** sorted by Ruff (standard library, third party, then `kroner`).
- **Typing:** every function, including tests, is fully annotated and must pass `mypy --strict`. Use modern syntax (`list[int]`, `X | None`), and narrow optionals with `assert x is not None` or an `if` rather than `# type: ignore`.
- **Strings:** use f-strings, not `%` or `.format()`.
- **Errors:** raise `ValueError` with a clear message for bad input, and chain the cause with `raise ... from error`.
- **Docstrings:** one-line summary for every public class and method.
- **Tests:** pytest in `tests/`, grouped into `Test*` classes. Use `@pytest.mark.parametrize` with tuple argument names, and pass `match=` to `pytest.raises`.
- **Lint rules:** pycodestyle (E, W), pyflakes (F), isort (I), bugbear (B), pyupgrade (UP), simplify (SIM), comprehensions (C4), pytest style (PT), Ruff-specific (RUF).
