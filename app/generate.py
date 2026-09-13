import requests
import vobject
import os
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


def fetch_contacts():
    validate_config()
    headers = {"Depth": "1"}
    r = requests.request(
        "PROPFIND",
        CARDDAV_URL,
        auth=(USERNAME, PASSWORD),
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()

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

        if not is_collection:
            contacts.append(resolved_href)

    return contacts


def generate_ics():
    validate_config()
    ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Birthday Export//EN\n"

    for href in fetch_contacts():
        try:
            card = requests.get(href, auth=(USERNAME, PASSWORD), timeout=30)
            card.raise_for_status()
            v = vobject.readOne(card.text)
            if hasattr(v, "bday"):
                name = v.fn.value

                if should_ignore(name):
                    print(f"Ignoring: {name}")
                    continue

                date = v.bday.value
                ics += (
                    "BEGIN:VEVENT\n"
                    f"SUMMARY:{name} Geburtstag\n"
                    f"DTSTART;VALUE=DATE:{date.strftime('%Y%m%d')}\n"
                    "RRULE:FREQ=YEARLY\n"
                    "END:VEVENT\n"
                )
        except Exception:
            pass

    ics += "END:VCALENDAR"

    with open(OUTPUT_FILE, "w") as f:
        f.write(ics)


if __name__ == "__main__":
    generate_ics()
