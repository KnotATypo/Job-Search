import sqlite3

from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import sites
import util

app = Flask(__name__)

options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)


@app.route("/", methods=["GET", "POST"])
def jobs():
    connection = sqlite3.connect(database="jobs.db")
    connection.autocommit = True
    cursor = connection.cursor()

    if request.method == "POST":
        file = request.form["file"]
        if "interested" in request.form:
            cursor.execute(f"UPDATE job_search SET status='interested_read' WHERE file='{file}'")
        elif "not_interested" in request.form:
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE file='{file}'")
            util.del_job_description(file)
        connection.commit()

    cursor.execute("SELECT id, title, company, file, site, duplicate FROM job_search WHERE status='interested'")
    result = cursor.fetchone()
    if result is None:
        return "You currently have no remaining <i>interested</i> jobs"

    site = sites.get_site_instance(result[4], driver)
    try:
        util.download_job_description(result, site)
        content = util.get_job_description(result[3])
    except FileNotFoundError:
        link = site.build_job_link(result[0])
        content = f"Could not find file. Try this link: <a target='_blank' href='{link}'>{link}</a>"

    duplicate_status = False
    if result[5] is not None:
        duplicate_status = util.get_duplicate_status(result[0], cursor)

    connection.close()

    return (
        "<style>input {border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;}</style>"
        + '<form method="post">'
        + f'<input type="hidden" name="file" value="{result[3]}"/>'
        + '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>'
        + '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>'
        + f"{f'<br>Duplicate status is: {duplicate_status}' if duplicate_status else ''}"
        + f"<hr><h1>{result[1]}<br>{result[2]}</h1>{content}<hr>"
        + '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>'
        + '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>'
        + "</form>"
    )


if __name__ == "__main__":
    app.run(debug=True)
