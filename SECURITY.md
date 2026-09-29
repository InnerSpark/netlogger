# Security

## Reporting a problem

Please **don't open a public issue** for security problems. Use GitHub's private reporting instead: **Security → Report a vulnerability** on this repo.

Include what you found, how to reproduce it, and what version you ran. You'll get a reply within a week.

## What's in scope

- Getting into the dashboard or API without a valid login
- An operator doing admin-only things
- Anything that makes the logger transmit or send commands to Asterisk beyond connect, disconnect, and list links
- Command injection through node numbers or other input

## Running it safely

- Keep the dashboard on your LAN or a VPN. If it faces the internet, put it behind HTTPS and set `COOKIE_SECURE=1`.
- Give the AMI user only `command` rights and `permit` only the logger's address.
- Keep `.env` private. It holds your AMI secret.
