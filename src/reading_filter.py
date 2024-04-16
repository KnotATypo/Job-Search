import psycopg2
from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import sites
import util

app = Flask(__name__)

connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
connection.autocommit = True

options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

seek = sites.Seek(connection)
jora = sites.Jora(connection, driver)
indeed = sites.Indeed(connection, driver)


@app.route('/', methods=['GET', 'POST'])
def jobs():
    cursor = connection.cursor()

    if request.method == 'POST':
        file = request.form['file']
        if 'interested' in request.form:
            cursor.execute(f"UPDATE job_search SET status='interested_read' WHERE file='{file}'")
        elif 'not_interested' in request.form:
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE file='{file}'")
            util.del_job_description(file)
        connection.commit()

    cursor.execute("SELECT id, title, company, file, site, duplicate FROM job_search WHERE status='interested'")
    result = cursor.fetchone()
    if result is None:
        return 'You currently have no remaining <i>interested</i> jobs'

    try:
        if result[4] == 'seek':
            link = seek.build_job_link(result[0])
            util.download_job_description(result, seek)
        elif result[4] == 'jora':
            link = jora.build_job_link(result[0])
            util.download_job_description(result, jora)
        elif result[4] == 'indeed':
            link = indeed.build_job_link(result[0])
            util.download_job_description(result, indeed)
        content = util.get_job_description(result[3])
    except FileNotFoundError:
        content = f"Could not find file. Try this link: <a target='_blank' href='{link}'>{link}</a>"

    duplicate_status = False
    if result[5] is not None:
        duplicate_status = util.get_duplicate_status(result[0], cursor)

    return \
            '<style>input {border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;}</style>' + \
            '<form method="post">' + \
            f'<input type="hidden" name="file" value="{result[3]}"/>' + \
            '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>' + \
            '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>' + \
            f"{f'<br>Duplicate status is: {duplicate_status}' if duplicate_status else ''}" + \
            f'<hr><h1>{result[1]}<br>{result[2]}</h1>{content}<hr>' + \
            '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>' + \
            '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>' + \
            '</form>'


if __name__ == '__main__':
    app.run(debug=True)
