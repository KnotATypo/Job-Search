import sqlite3
import os

from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def hello_world():
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()

    if request.method == 'POST':
        file = request.form['file']
        print(file)
        if 'interested' in request.form:
            cursor.execute(f"UPDATE jobs SET status='interested_read' WHERE file='{file}'")
        elif 'not_interested' in request.form:
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE file='{file}'")
            os.remove(f'job_descriptions/{file}')
        connection.commit()

    result = cursor.execute("SELECT id, title, company, file FROM jobs WHERE status='interested'").fetchone()
    if result is None:
        return 'You currently have no remaining <i>interested</i> jobs'
    with open(f'job_descriptions/{result[3]}') as f:
        content = f.read()
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
