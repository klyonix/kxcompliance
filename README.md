## KlyONIX Compliance

Statutory filings, licences, registrations, certificates and legal matters on time, for an Indian
company or for a CA/CS firm's clients. Built on Frappe and ERPNext, with an app that works on a
phone as well as a desk.

### What it does

**For a company**
- **Compliance calendar.** Tell it the kind of company and its registrations (GST, TAN, PF, ESI,
  PT and more); it lists the recurring returns and payments under the Companies Act, GST, income
  tax and TDS, and makes each filing before it falls due, with who prepares and who checks it.
- **Filings with proof.** Each filing records when it was filed, the acknowledgement number, the
  proof and what was paid, with what a late filing costs. A reviewed return is marked filed by
  someone other than its preparer; a one-person team can file its own, and the record says so.
- **Register.** Licences, certificates, insurance, subscriptions and contracts, with renewals and
  reminders before they expire.
- **Legal.** Notices, cases, hearings and trademarks, with their dates and deadlines.
- **Licence checks on sales and purchases.** A quotation, order or invoice for a customer or
  supplier without a valid licence warns, or stops submission, by the rules you set.
- **Reminders and escalation** by email before anything falls due, and to a manager when it is
  missed. Overview, compliance score, reports and Excel export.

**For a CA/CS firm**
- **Clients and their companies**, with the firm's team on each client, and client logins that
  see only their own companies, filings and documents.
- **Document requests** to clients, one at a time or in bulk, uploaded straight from the client's
  login.
- **Billing** through ERPNext: rate cards, bills from filed returns and recurring fees, GST
  (CGST/SGST or IGST by state), payments with TDS, advances, credit notes, write-offs, overdue
  reminders and a statement of account per client.

**Also**
- A mobile-friendly app at `/compliance`, with offline reading, light and dark themes, and English
  and Hindi.
- Privacy built for India's DPDP Act: a privacy notice, requests from people about their data,
  breach records, and PAN and mobile numbers masked from all but managers (on Frappe 15, which
  cannot mask a field, hidden from them instead).

### Requirements

- Frappe Framework 15 and ERPNext 15 (this branch, `version-15`). New features are made on
  `version-16` first; this branch is a one-time port for sites still on version 15.
- Python 3.11, Node 18 or later, MariaDB
- Chrome or Chromium on the server, which prints bills, receipts and statements
  (`apt install chromium`, or set `chrome_path` in the site config)

### Installation

On Frappe Cloud, add **KlyONIX Compliance** to your site from the Marketplace.

On your own server, with [bench](https://github.com/frappe/bench):

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app erpnext --branch version-15
bench get-app https://github.com/klyonix/kxcompliance --branch version-15
bench --site <your-site> install-app kxcompliance
```

Then open `https://<your-site>/compliance`. A Compliance Manager is taken through a short setup:
an organisation or a CA/CS firm, the first company, its registrations and who looks after its
filings.

### Using the app

See the [user guide](USER_GUIDE.md). The same answers are on the Help page inside the app.

### Contributing

Issues and pull requests are welcome on GitHub.

This app uses `pre-commit` for formatting and linting (ruff, eslint, prettier):

```bash
cd apps/kxcompliance
pre-commit install
```

Tests:

```bash
bench --site <test-site> set-config allow_tests true
bench --site <test-site> run-tests --app kxcompliance
cd apps/kxcompliance/frontend && yarn test
```

The user guide is built from the app's Help answers (`frontend/src/help/articles.js`). After
changing them, rebuild it from `frontend/` with `node scripts/user-guide.mjs`; a test fails until
you do.

### License

Copyright (c) 2026 KlyONIX Tech Consulting Pvt Ltd.

GNU Affero General Public License v3.0 (AGPL-3.0); see [license.txt](license.txt). Anyone who
runs a changed copy for others to use over a network must share the changed source with them.
