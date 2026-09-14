# Birthday ICS Generator

A small Docker service that generates a `birthdays.ics` file from your Nextcloud contacts via CardDAV once per day and serves it through a built‑in web server.

This is to circumvent the limitiation that the generated Contacts Birthday calendar cannot be shared as ics in Nextcloud (see [Nextcloud Server #40331](https://github.com/nextcloud/server/issues/40331)).

I needed this to use the Birthday calendar of my Nextcloud contacts for MagicMirror², but this may be of use for other applications.

It's mostly vibe-coded, but it does the job.

## Features

- Daily birthday extraction and ICS generation from CardDAV contacts
- Serve the ICS via a built‑in web server
- Ignore list for filtering out specific names
- Small and easy Docker container

## Quick Installation

Create a folder:

```bash
mkdir birthday-ics && cd birthday-ics
```

Download the `docker-compose.yml`:

```bash
curl -O https://raw.githubusercontent.com/s-martin/birthday-ics/main/docker-compose.yml.TEMPLATE && mv docker-compose.yml.TEMPLATE docker-compose.yml
```

Edit the configuration variables.

Run the container:

```bash
docker compose up -d
```

Your ICS feed will be available at:

```Code
http://<server>:8080/birthdays.ics
```

### Manual Regeneration

If you want to regenerate the ICS file immediately:

```bash
docker exec birthday-ics python3 /app/generate.py
```

## Configuration

The container is configured entirely through environment variables.

### Required Variables

| Variable | Description |
| -- | -- |
| CARDDAV_URL | URL of your Nextcloud CardDAV address book. Example: <https://cloud.example.com/remote.php/dav/addressbooks/users/john/contacts/> |
| CARDDAV_USER | Username for CardDAV authentication |
| CARDDAV_PASS | Password (app-specific password recommended) |

### Optional Variables

| Variable | Description |
| -- | -- |
| IGNORE_NAMES | Comma‑separated list of substrings. Any contact whose name contains one of these substrings will be ignored. Matching is case‑insensitive and substring‑based. Example: `IGNORE_NAMES="Test,Müller,Example"` |

#### Ignore List Examples

| Ignore | Skips |
| -- | -- |
| Müller | Müller GmbH, Family Müller |
| Max | Max Mustermann, Maximilian |
| Test | Testperson, Testkunde |

### Cron Schedule

The ICS file is regenerated daily at 03:00 server time

### Volumes

`./data:/data` stores the generated birthdays.ics file. This ensures the ICS file persists across container restarts.
