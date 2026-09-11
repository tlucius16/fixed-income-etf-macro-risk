# Tests

- `hedge_design/`: active accounting, optimization, data and reporting checks.
- `workflow/`: active reproduction, preservation and repository boundaries.
- `../legacy/unified/tests/`: all retired workflow tests, including optional
  ThetaData and Julia diagnostics. None are deleted.

From the repository root:

```bash
python -m pytest tests/ -q
RUN_THETA_LIVE_TEST=0 RUN_JULIA_AMERICAN=0 RUN_JULIA_BOOTSTRAP=0 \
  python -m pytest tests/ legacy/unified/tests/ -q
```

Default active checks do not fetch data or execute legacy notebooks.
