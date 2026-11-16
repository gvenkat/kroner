## Code style

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
