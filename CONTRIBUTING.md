# Contributing

Thanks for your interest in improving the Brink Flair integration! Contributions of any size are welcome:

- reporting a bug
- reporting whether the integration works with **your Brink model** (only the Flair 400 is tested so far)
- improving the documentation, translations or dashboards
- submitting a fix or a new feature

## Questions and ideas

For setup help (wiring, RS-485 adapters, Modbus settings) use [Discussions → Q&A](https://github.com/Barracuda1984/ha-brink-flair/discussions/categories/q-a).
Feature ideas go to [Discussions → Ideas](https://github.com/Barracuda1984/ha-brink-flair/discussions/categories/ideas).

## Reporting bugs and model compatibility

Use the [issue forms](https://github.com/Barracuda1984/ha-brink-flair/issues/new/choose):

- **Bug report** — include the integration and Home Assistant versions, your model and control board, and **debug logs**:

  ```yaml
  logger:
    default: warning
    logs:
      custom_components.brink_flair: debug
      pymodbus: debug
  ```

- **Working model report** — tell us which model, board and features work. Reports are added to the compatibility table in the README.

## Pull requests

This project follows the [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow):

1. Fork the repository and create a branch from `master`.
2. Make your change — keep pull requests focused on one topic.
3. If you add or change behaviour, add or update tests in `tests/`.
4. Update `README.md` if entities, options or setup steps change, and add a line to the `[Unreleased]` section of `CHANGELOG.md`.
5. If you change UI strings, edit `strings.json` and mirror the change in `translations/en.json`.
6. Make sure the checks pass (see below) and open a pull request.

### Sign your commits (DCO)

Every commit must be signed off to certify the [Developer Certificate of Origin](https://developercertificate.org/):

```bash
git commit -s -m "fix: describe the change"
```

This adds a `Signed-off-by: Your Name <you@example.com>` line to the commit message.

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes, as in the existing history: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`, `refactor:`.

## Development

### Environment

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements_test.txt
```

Run Home Assistant with the integration loaded:

```bash
hass -c .
```

Without real hardware you can point the integration at a virtual serial port or a Modbus simulator; please mention in the PR whether you tested on a real unit.

### Code style

Follow the [Home Assistant development guidelines](https://developers.home-assistant.io/docs/development_guidelines): type hints, async I/O only (no blocking calls in the event loop), and formatting compatible with [Ruff](https://docs.astral.sh/ruff/), which Home Assistant core uses:

```bash
pip install ruff
ruff check custom_components tests
ruff format custom_components tests
```

### Modbus changes

The register map lives in `custom_components/brink_flair/const.py`. When adding registers:

- cite the source (Brink Modbus documentation, register number and scaling),
- keep reads batched in `coordinator.py` — every extra Modbus transaction slows down the poll cycle,
- be careful with writes: never write registers you have not verified on a real unit.

### Checks

```bash
pytest                 # unit tests
```

GitHub Actions runs the test suite plus **HACS** and **hassfest** validation on every pull request.

## License

By contributing, you agree that your contributions will be licensed under the [GNU GPL v3](LICENSE), the license of this project.
