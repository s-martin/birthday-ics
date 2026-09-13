import requests
import vobject
import os
from urllib.parse import urljoin

CARDDAV_URL = os.getenv("CARDDAV_URL")
USERNAME = os.getenv("CARDDAV_USER")
PASSWORD = os.getenv("CARDDAV_PASS")

IGNORE_LIST = [
    name.strip().lower()
    for name in os.getenv("IGNORE_NAMES", "").split(",")
    if name.strip()
]

OUTPUT_FILE = "/data/birthdays.ics"


def should_ignore(name: str) -> bool:
    lname = name.lower()
    return any(ignore in lname for ignore in IGNORE_LIST)


def fetch_contacts():
    headers = {"Depth": "1"}
    r = requests.request(
        "PROPFIND",
        CARDDAV_URL,
        auth=(USERNAME, PASSWORD),
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    return r.text.split("<d:href>")[1:]


def generate_ics():
    missing = [k for k, v in {
        "CARDDAV_URL": CARDDAV_URL,
        "CARDDAV_USER": USERNAME,
        "CARDDAV_PASS": PASSWORD,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Birthday Export//EN\n"

    for href in fetch_contacts():
        try:
            url = urljoin(CARDDAV_URL, href.split("</d:href>")[0])
            card = requests.get(url, auth=(USERNAME, PASSWORD), timeout=30)
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
