from flask import Flask, send_file

app = Flask(__name__)


@app.route("/birthdays.ics")
def birthdays():
    return send_file("/data/birthdays.ics", mimetype="text/calendar")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
