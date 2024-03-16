import os
import sqlite3

from flask import Flask, request

import sites

app = Flask(__name__)


# @app.route('/', methods=['GET'])
# def home():
#     connection = sqlite3.connect('jobs.db')
#     cursor = connection.cursor()
#
#     new_count = cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IS 'new'").fetchone()[0]
#     interested_count = cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IS 'interested'").fetchone()[0]
#     not_interested_count = cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IS 'not_interested'").fetchone()[0]
#     interested_read_count = cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IS 'interested_read'").fetchone()[0]
#     easy_filter_count = cursor.execute("SELECT COUNT(*) FROM jobs WHERE status IS 'easy_filter'").fetchone()[0]
#
#     return


@app.route('/', methods=['GET', 'POST'])
def jobs():
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()

    if request.method == 'POST':
        file = request.form['file']
        print(file)
        if 'interested' in request.form:
            cursor.execute(f"UPDATE jobs SET status='interested_read' WHERE file='{file}'")
        elif 'not_interested' in request.form:
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE file='{file}'")
            if os.path.exists(f'job_descriptions/{file}'):
                os.remove(f'job_descriptions/{file}')
        connection.commit()

    result = cursor.execute("SELECT id, title, company, file FROM jobs WHERE status='interested'").fetchone()
    print(result)
    if result is None:
        return 'You currently have no remaining <i>interested</i> jobs'

    try:
        with open(f'job_descriptions/{result[3]}') as f:
            content = f.read()
    except FileNotFoundError:
        content = f"Could not find file. Try this link: <a target='_blank' href='{sites.Seek(None).JOB_URL}{result[0]}'>{sites.Seek(None).JOB_URL}{result[0]}</a>"

    return \
            '<style>input {border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;}</style>' + \
            '<form method="post">' + \
            f'<input type="hidden" name="file" value="{result[3]}"/>' + \
            '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>' + \
            '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>' + \
            f'<hr><h1>{result[1]}<br>{result[2]}</h1>{content}<hr>' + \
            '<input type="submit" name="interested" style="background-color: #04AA6D" value="Interested"/>' + \
            '<input type="submit" name="not_interested" style="background-color: #f44336" value="Not Interested"/>' + \
            '</form>'


if __name__ == '__main__':
    app.run(debug=True)
