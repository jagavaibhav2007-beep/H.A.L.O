# Contributing

Bug reports, design discussion, and private security reports are welcome. Because
the project license has not yet been selected, external code contributions are not
being accepted as redistributable open-source contributions at this stage.

For repository work, create a focused branch, preserve unrelated changes, and
follow [DEVELOPMENT.md](DEVELOPMENT.md). Behavior changes require a failing test
first. Run `./verify.ps1 -PythonCommand '.\.venv\Scripts\python.exe'` before
requesting review, and include the reason for the change and the exact verification
evidence. Never commit credentials, user data, session files, model caches, build
artifacts, or absolute developer paths.

Architecture changes must update the matching PRD, `systemdesign/`, `techstack/`,
and `ui_ux/` sources when their claims change. Dependency changes must keep the
relevant lock synchronized and pass `scripts/check-locks.ps1`.
