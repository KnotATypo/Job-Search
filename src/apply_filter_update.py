import json

import psycopg2

connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
connection.autocommit = True
cursor = connection.cursor()

with open('../config.json') as f:
    config = json.load(f)
    blacklist = config['title-blacklist']

cursor.execute("SELECT status, title, id FROM job_search")
jobs = cursor.fetchall()
for job in jobs:
    contains = any([x in job[1].lower() for x in blacklist])
    if contains and job[0] != 'easy_filter':
        cursor.execute(f"UPDATE job_search SET status = 'easy_filter' WHERE id = '{job[2]}'")
        print(job)
    elif not contains and job[0] == 'easy_filter':
        cursor.execute(f"UPDATE job_search SET status = 'new' WHERE id = '{job[2]}'")
        print(job)
