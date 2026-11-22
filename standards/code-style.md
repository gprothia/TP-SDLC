# Code style

Tools enforce style, so reviews don't have to.
- STY-1. Python: `ruff format` and `ruff check` (settings in `ruff.toml`). Includes security
  checks (`S` rules) and import order.
- STY-2. TypeScript tests: `eslint` (settings in `tests/ui/eslint.config.mjs`).
- STY-3. Agents run both before every commit; CI runs them on every PR and blocks on failure.
- STY-4. Names say what things are: `create_request`, not `handle2`. Comments say why, not what.
