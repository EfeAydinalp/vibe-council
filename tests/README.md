# Tests

Stdlib-only smoke tests (no extra dependencies). They never make real OpenRouter
calls and never require a real API key.

Run from the repo root:

```bash
python -m unittest discover -s tests -t .
```

`pytest` also works if you have it installed:

```bash
pytest tests
```

CI runs the `unittest` command on Ubuntu and Windows (see `.github/workflows/ci.yml`).
