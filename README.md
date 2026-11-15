### KlyONIX Compliance

Keeps statutory filings, licences, registrations, certificates and legal matters on time, for a
company or for a CA/CS firm's clients, with reminders before anything falls due.

### Using the app

See the [user guide](USER_GUIDE.md). The same answers are on the Help page inside the app.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app kxcompliance
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/kxcompliance
pre-commit install
```

The user guide is built from the app's Help answers (`frontend/src/help/articles.js`). After
changing them, rebuild it from `frontend/` with `node scripts/user-guide.mjs`; a test fails
until you do.

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
