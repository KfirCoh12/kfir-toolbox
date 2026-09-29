# Local Windows desktop mode

This is the manual-first local version of Kfir Toolbox. It opens the existing
Streamlit interface in a desktop window and binds its server to 127.0.0.1 only.
The wrapper does not change engineering calculations.

## First run

1. Install Python 3.12+ for Windows and enable **Add Python to PATH**.
2. Double-click `install-local.bat`.
3. Double-click `START_LOCAL.bat`.

The local install uses `requirements-local.txt`; it does not install OpenAI or
require an API key. The existing `requirements.txt` remains for the current
development/AI workflow.

## Data and privacy

Board Planner persistence continues to use the existing local storage under the
current user's home directory (normally
`~/.kfir-toolbox/board-planner/last_board.json`). This milestone does not add
multiple named projects or backup/restore. The local web server binds to
loopback and is not intended to be reachable from other computers.

## Current milestone limitations

- Python must be installed; this is not yet a standalone installer.
- WebView2 Runtime may be required by the Windows webview environment.
- The AI page is excluded from this local app phase; its source is retained
  separately for a later optional phase.
- Validate startup, shutdown, persistence, and existing tests on Windows before
  distributing it.
