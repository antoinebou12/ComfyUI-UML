# Security policy

## Supported versions

Security fixes are applied to the latest release on the default branch (`main`). Older tags may not receive backports unless the issue is critical; open an advisory to discuss backport needs.

## Reporting a vulnerability

If you believe you have found a security vulnerability in ComfyUI-UML, please report it responsibly:

1. **Preferred:** [Open a GitHub Security Advisory](https://github.com/antoinebou12/ComfyUI-UML/security/advisories/new). The report stays private until it is published.
2. **Alternative:** Email or open a regular issue **without** exploit details, and ask to be contacted privately for follow-up.

Include enough context to reproduce or understand the risk (affected component, version or commit, and impact). Please do not post working exploits in public issues.

## What we do next

Maintainers will acknowledge receipt, assess severity, and work toward a fix and coordinated disclosure when appropriate.

## Hardening in this repository

- **CodeQL** runs on pushes and pull requests to `main` / `master` (Python analysis).
- **Dependency review** runs on pull requests to flag known-vulnerable dependency changes.
- **Dependabot** and **Renovate** propose dependency and GitHub Actions updates (see [CONTRIBUTORS.md](CONTRIBUTORS.md)).

## Proxy and network surface

The HTTP proxy used for diagram URLs is restricted to **kroki.io** / **www.kroki.io** only. If you find a bypass or SSRF, report it via an advisory.
