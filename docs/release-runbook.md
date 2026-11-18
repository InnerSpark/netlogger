# Net Logger Release Runbook

## Before release
- [ ] Version bumped in `netlogger/__init__.py` and `pyproject.toml`
- [ ] CHANGELOG.md: move Unreleased into the version, with the date
- [ ] accessibility-audit.md current (re-test anything the release changed)
- [ ] privacy.md current
- [ ] licensing.md current (new dependencies listed)
- [ ] security.md current, no secrets in the repo
- [ ] `scripts/pentest-live.sh` run against a test install, results in the report
- [ ] `scripts/release-check.sh .` says RELEASE OK (pen test report says Result: Pass)

## Build and ship
1. Merge the release PR into `main` (CI green).
2. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. GitHub Actions builds the release (with `web-dist.tgz` for servers without Node) and the Docker image on ghcr.io.
4. Check the release page and that `docker pull ghcr.io/innerspark/netlogger:X.Y.Z` works.
5. Update your own server: copy the release, run `sudo ./install.sh --no-restart` (it backs up the database first).
6. Post a short note where hams will see it (see go-to-market.md).

## Rollback
1. Server: stop the service, restore the newest file in `/var/lib/netlogger/backups/` over `netlog.db`, check out the previous tag, run `install.sh` again.
2. Docker: pin the previous image tag in `compose.yaml`, `docker compose up -d`.
3. Mark the bad release as a pre-release on GitHub and say why in its notes.

## Credentials and accounts
- GitHub (InnerSpark org): push, releases, packages.
- No other accounts are needed to release. Server owners bring their own Apple push key if they want push.
