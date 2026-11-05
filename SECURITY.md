# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub: on this repository's Security tab, choose "Report a vulnerability"
([private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
Do not open a public issue or pull request for a vulnerability.

A useful report says which template version and options are affected, how to reproduce it in a freshly generated app,
and what an attacker could do with it.

## Scope

- The template itself: `copier.yml`, the files under `template/`, and the workflow in `.github/`.
- What a freshly generated app does before anyone changes it: the backend, the passkey accounts, the compose and
  deploy files, and the backup scripts.

Changes an app made after it was generated are that app's own concern.

## Rules for testing

- Test against an app you generated and run yourself. This repository has no hosted service.
- Do not test against anyone else's deployment of a generated app.
