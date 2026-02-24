# Publishing to the Comfy Registry

The workflow **.github/workflows/publish-node.yml** publishes the node when **pyproject.toml** changes on `main` or `master` (push to those branches).

## Setup

1. Create a [personal access token](https://docs.comfy.org/registry/publishing) on the Comfy Registry for your publisher.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: **REGISTRY_ACCESS_TOKEN**
   - Value: your token

## Troubleshooting

- **Publish job fails**: Ensure `REGISTRY_ACCESS_TOKEN` is set. The workflow prints a clear error if the secret is missing.
- **"Failed to validate token"**: The token must be for the publisher in `pyproject.toml` (`PublisherId`), and the Comfy Registry publisher must be linked to this repository.

Without the secret, the publish job fails with a message pointing to the Comfy Registry publishing docs.
