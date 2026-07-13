# Contributing

Thanks for considering a contribution to this project.

## Scope

This repo tracks a working, OS 3.00-compatible port of Red Pitaya's official Web App Example, plus the investigation notes explaining why the stock example doesn't build as-is. Contributions in scope:

- Fixes for build/deploy issues on other Red Pitaya boards or OS versions
- Additional findings for `docs/FINDINGS.md` (new failure modes, other SDK versions, other boards)
- Improvements to the example app itself (UI, backend logic) as a learning reference
- Tooling improvements (the SSH/SCP helper scripts, build scripts)

## Before you start

- If you're fixing a build error, please include the **exact compiler/tool output** in your PR description — that's what makes `docs/FINDINGS.md` useful as a reference for others hitting the same issue.
- If you're testing against different hardware (e.g. a 125-14 instead of a 125-10) or a different OS version, say so explicitly — RAM size and SDK versions materially change what breaks.

## Development workflow

1. Fork the repo and create a branch off `main`.
2. Make your change. If it changes behavior on-device, test it against real hardware — this project doesn't have a way to build/verify against emulated Red Pitaya hardware.
3. Update `docs/FINDINGS.md` if you hit and fixed a new issue — treat it as an append-only investigation log, not just a changelog.
4. Open a pull request describing what you changed and why, and what you tested it against (board model, OS version).

## Commit signing

Commits in this repository are signed. Please sign your commits too:

```sh
git config commit.gpgsign true
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub   # or your preferred signing key
```

And add your public key as a [signing key on GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#ssh-commit-signature-verification) so commits show as verified.

## Reporting issues

When filing an issue against a build/deploy failure, please include:
- Board model (e.g. STEMlab 125-10, 125-14)
- OS version (`cat /opt/redpitaya/version.txt` on the board)
- Full error output
- `free -h` output if it's a compile-time failure (RAM constraints are a recurring cause on this hardware)

## Code of conduct

Be respectful and constructive. This is a small hobbyist/hardware project — assume good faith, and keep discussion focused on the technical problem.
