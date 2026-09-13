import requests
import vobject
import os
import sys
from datetime import date as date_type, datetime
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

CARDDAV_URL = os.getenv("CARDDAV_URL")
USERNAME = os.getenv("CARDDAV_USER")
PASSWORD = os.getenv("CARDDAV_PASS")

IGNORE_LIST = [
    name.strip().lower()
    for name in os.getenv("IGNORE_NAMES", "").split(",")
    if name.strip()
]

OUTPUT_FILE = "/data/birthdays.ics"


def validate_config():
    missing = [k for k, v in {
        "CARDDAV_URL": CARDDAV_URL,
        "CARDDAV_USER": USERNAME,
        "CARDDAV_PASS": PASSWORD,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def should_ignore(name: str) -> bool:
    lname = name.lower()
    return any(ignore in lname for ignore in IGNORE_LIST)


def parse_bday_year(text):
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).year
        except ValueError:
            continue
    return None


def parse_bday(value):
    """Parse a vCard BDAY value into a date object.

    vobject usually parses BDAY into a date/datetime object, but falls back
    to returning the raw string when the value doesn't match the expected
    formats (e.g. year-less birthdays like "--02-03" or "--0203"). This
    normalizes both cases and returns None if the value can't be parsed.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_type):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("--"):
            digits = text[2:].replace("-", "")
            if len(digits) == 4 and digits.isdigit():
                month, day = int(digits[:2]), int(digits[2:])
                try:
                    # No year given; use a fixed leap year as placeholder.
                    return date_type(1604, month, day)
                except ValueError:
                    return None
        year = parse_bday_year(text)
        if year is not None:
            return datetime.strptime(text, "%Y-%m-%d" if "-" in text else "%Y%m%d").date()
    return None


def format_bday_summary(name, value):
    raw_value = None
    if hasattr(value, "serialize"):
        serialized = value.serialize().strip()
        if ":" in serialized:
            raw_value = serialized.split(":", 1)[1].strip()
        value = getattr(value, "value", value)

    year = None
    if raw_value:
        if not raw_value.startswith("--"):
            year = parse_bday_year(raw_value)
    elif isinstance(value, datetime):
        year = value.year
    elif isinstance(value, date_type):
        year = value.year
    elif isinstance(value, str):
        text = value.strip()
        if not text.startswith("--"):
            year = parse_bday_year(text)

    return f"{name} ({year})" if year is not None else name


def fetch_contacts():
    validate_config()
    headers = {"Depth": "1"}
    try:
        r = requests.request(
            "PROPFIND",
            CARDDAV_URL,
            auth=(USERNAME, PASSWORD),
            headers=headers,
            timeout=30,
        )
    except requests.exceptions.Timeout as exc:
        raise ConnectionError(
            f"Timed out connecting to CardDAV server at {CARDDAV_URL}"
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"Could not connect to CardDAV server at {CARDDAV_URL}: {exc}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ConnectionError(
            f"CardDAV request to {CARDDAV_URL} failed: {exc}"
        ) from exc

    if r.status_code in (401, 403):
        raise ConnectionError(
            f"CardDAV authentication failed (HTTP {r.status_code}). "
            "Check CARDDAV_USER/CARDDAV_PASS."
        )
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        raise ConnectionError(
            f"CardDAV server returned an error (HTTP {r.status_code}) for {CARDDAV_URL}: {exc}"
        ) from exc

    contacts = []
    base_url = CARDDAV_URL.rstrip("/")
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as exc:
        raise ValueError("CardDAV PROPFIND returned invalid XML") from exc
    root_local_name = root.tag.split("}", 1)[-1]
    if root_local_name != "multistatus":
        raise ValueError("CardDAV PROPFIND returned unexpected XML payload")

    dav_ns = ""
    if root.tag.startswith("{") and "}" in root.tag:
        dav_ns = root.tag[1:].split("}", 1)[0]

    def qname(name: str) -> str:
        return f"{{{dav_ns}}}{name}" if dav_ns else name

    for response in root.findall(qname("response")):
        href = response.find(qname("href"))
        if href is None or not href.text:
            continue

        resolved_href = urljoin(CARDDAV_URL, href.text).rstrip("/")
        if resolved_href == base_url:
            continue

        is_collection = False
        is_vcard = href.text.lower().endswith(".vcf")
        for propstat in response.findall(qname("propstat")):
            status = propstat.findtext(qname("status"), default="")
            status_parts = status.split()
            if len(status_parts) < 2 or status_parts[1] != "200":
                continue
            prop = propstat.find(qname("prop"))
            if prop is None:
                continue
            resourcetype = prop.find(qname("resourcetype"))
            if resourcetype is not None and resourcetype.find(qname("collection")) is not None:
                is_collection = True
                break
            content_type = prop.findtext(qname("getcontenttype"), default="").lower()
            if "text/vcard" in content_type:
                is_vcard = True

        if not is_collection and is_vcard:
            contacts.append(resolved_href)

    return contacts


def generate_ics():
    validate_config()
    ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Birthday Export//EN\n"

    contacts = fetch_contacts()
    print(f"Found {len(contacts)} contact(s) in CardDAV address book")

    added = 0
    ignored = 0
    skipped_no_bday = 0
    errors = 0

    for href in contacts:
        try:
            card = requests.get(href, auth=(USERNAME, PASSWORD), timeout=30)
            card.raise_for_status()
            v = vobject.readOne(card.text)
            if hasattr(v, "bday"):
                name = v.fn.value

                if should_ignore(name):
                    print(f"Ignoring: {name}")
                    ignored += 1
                    continue

                date = parse_bday(v.bday.value)
                if date is None:
                    print(
                        f"Warning: could not parse birthday for {name}: {v.bday.value!r}",
                        file=sys.stderr,
                    )
                    skipped_no_bday += 1
                    continue

                ics += (
                    "BEGIN:VEVENT\n"
                    f"SUMMARY:{format_bday_summary(name, v.bday)}\n"
                    f"DTSTART;VALUE=DATE:{date.strftime('%Y%m%d')}\n"
                    "RRULE:FREQ=YEARLY\n"
                    "END:VEVENT\n"
                )
                added += 1
            else:
                skipped_no_bday += 1
        except requests.exceptions.RequestException as exc:
            errors += 1
            print(f"Warning: could not fetch contact {href}: {exc}", file=sys.stderr)
        except Exception as exc:
            errors += 1
            print(f"Warning: could not process contact {href}: {exc}", file=sys.stderr)

    ics += "END:VCALENDAR"

    with open(OUTPUT_FILE, "w") as f:
        f.write(ics)

    print(
        f"Wrote {added} birthday event(s) to {OUTPUT_FILE} "
        f"(ignored: {ignored}, without birthday: {skipped_no_bday}, errors: {errors})"
    )


if __name__ == "__main__":
    try:
        generate_ics()
    except (ValueError, ConnectionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
