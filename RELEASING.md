# Releasing

## How to create a release

1. Ensure your changes are merged to `main`.
2. Create and push a version tag:

   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

   Tags must follow the `v*` pattern (e.g., `v1.0.0`, `v2.1.0`).

## What happens automatically

Pushing a `v*` tag triggers the **Build and Publish Docker Image to GHCR** workflow (`.github/workflows/docker-ghcr.yml`), which:

1. Builds the Docker image.
2. Pushes the image to GHCR with the version tag (e.g., `ghcr.io/s-martin/birthday-ics:v1.2.3`) and the `latest` tag.
3. Creates a GitHub Release for the tag with auto-generated release notes.

Pushes to `main` without a tag will build and push an image tagged with the branch name and commit SHA, but will **not** publish `latest` or create a GitHub Release.

## Verifying the release

- **GitHub Release**: <https://github.com/s-martin/birthday-ics/releases>
- **GHCR package**: <https://github.com/s-martin/birthday-ics/pkgs/container/birthday-ics>
