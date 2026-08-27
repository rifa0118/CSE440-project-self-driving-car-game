# Verification

Run on Windows after `setup_windows.bat`:

```bat
verify_project.bat
```

The script performs:

1. Python compilation;
2. the full pytest suite;
3. independent release verification, including 20 greedy episodes on each packaged best model and a real Pygame dummy-display smoke initialization;
4. `pip check` inside the isolated project virtual environment.

`tools/verify_release.py` can also be run directly. Without `--strict-pygame`, an environment that lacks Pygame is reported as `ENVIRONMENT_BLOCKED` for that one runtime layer instead of being mislabeled as a code failure or a PASS.
