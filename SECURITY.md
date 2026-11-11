# Security policy

## Vulnerabilities in the harness

If you find a security problem in the GuardrailBench code (the harness, adapters, scoring, or submission checks), report it privately through GitHub: open the repository's Security tab and choose "Report a vulnerability" (a private security advisory). Please do not open a public issue.

Include what you found, how to reproduce it, and what it affects. Maintainers aim to reply within 7 days.

## Keys and accounts

Never post a key, password or token in an issue, a pull request or a log. A vendor that takes part in an official round sends its account or key privately, through the contact route named in its participation request. If a secret is posted by mistake, revoke it first, then report it through the private form above.

## Guard bypasses found while benchmarking

GuardrailBench measures third-party guardrail products. If you find a way to bypass a product while using this project:

1. Tell the affected vendor first, using their own security contact.
2. Give them 90 days to respond and fix before you publish details.
3. After the window, or once the vendor has fixed it, you may publish.

Maintainers follow the same rule for anything they find.

## What not to post

Never post a working attack against a third-party product in an issue, pull request, or discussion. That includes proof-of-concept prompts that bypass a named product. Report them to the vendor instead. The practice cases are fake scenarios and are fine to discuss.

If a practice case seems to contain a real harmful payload, report it as a case issue without repeating the payload.
