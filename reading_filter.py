import os

import psycopg2
from flask import Flask, request

import sites

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def jobs():
    connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
    connection.autocommit = True
    cursor = connection.cursor()

    if request.method == 'POST':
        file = request.form['file']
        if 'interested' in request.form:
            cursor.execute(f"UPDATE job_search SET status='interested_read' WHERE file='{file}'")
        elif 'not_interested' in request.form:
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE file='{file}'")
            if os.path.exists(f'job_descriptions/{file}'):
                os.remove(f'job_descriptions/{file}')
        connection.commit()

    cursor.execute("SELECT id, title, company, file, site, duplicate FROM job_search WHERE status='interested'")
    result = cursor.fetchone()
    if result is None:
        return 'You currently have no remaining <i>interested</i> jobs'

    try:
        with open(f'job_descriptions/{result[3]}') as f:
            content = f.read()
    except FileNotFoundError:
        if result[4] == 'seek':
            link = sites.Seek(None).build_job_link(result[0])
        else:
            link = sites.Jora(None).build_job_link(result[0])
        content = f"Could not find file. Try this link: <a target='_blank' href='{link}'>{link}</a>"

    duplicate_status = False
    if result[5] is not None:
        duplicate_status = get_duplicate_status(result[0], cursor)

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


def get_duplicate_status(id_source, cursor):
    status = []
    cursor.execute(f"SELECT duplicate FROM job_search WHERE id='{id_source}'")
    for id_target in str(cursor.fetchone()[0]).split(','):
        cursor.execute(f"SELECT status FROM job_search WHERE id='{id_target}'")
        status.append(cursor.fetchone()[0])
    if 'applied' in status:
        return 'applied'
    if 'easy_filter' in status:
        return 'easy_filter'
    if 'interested_read' in status:
        return 'interested_read'
    if 'interested' in status:
        return 'interested'
    if all([x == 'not_interested' for x in status]):
        return 'not_interested'
    return '???'


if __name__ == '__main__':
    app.run(debug=True)
