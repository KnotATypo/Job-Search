import re
import sqlite3
import os
from sites import Seek
from collections import defaultdict

import requests
from html2text import html2text
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

SEARCH_TERMS = ['programmer', 'computer-science', 'software-engineer', 'software-developer']


def main():
    connection = setup()

    seek = Seek(connection)
    for term in SEARCH_TERMS:
        seek.download_new_jobs(term)

    deduplicate(connection)
    easy_filter(connection)


def setup():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    cursor.execute('CREATE TABLE IF NOT EXISTS jobs(id STRING UNIQUE, title STRING, company STRING, file STRING, duplicate BOOLEAN, status STRING, site STRING)')
    if not os.path.exists('job_descriptions'):
        os.mkdir('job_descriptions')

    return conn


def deduplicate(connection):
    jobs = os.listdir('job_descriptions')
    lookup = defaultdict(lambda: None)
    for i, job_source in enumerate(jobs):
        source_name = job_source[:job_source.rindex('-')]
        for j, job_comp in enumerate(jobs):
            if i == j or lookup[(job_source, job_comp)] is not None:
                continue
            comp_name = job_comp[:job_comp.rindex('-')]
            lookup[(job_comp, job_source)] = source_name == comp_name
    duplicates = set()
    for key in lookup:
        if lookup[key] == True:
            duplicates.add(key[0][key[0].rindex('-') + 1:key[0].index('.html')])
            duplicates.add(key[1][key[1].rindex('-') + 1:key[1].index('.html')])
    cursor = connection.cursor()
    for id in duplicates:
        cursor.execute(f'UPDATE jobs SET duplicate=true WHERE id={id}')
        connection.commit()


def easy_filter(connection):
    blacklist_terms = ['.net', 'senior', 'lead', 'architect', 'principal', 'graduate', 'director']
    cursor = connection.cursor()
    counter = 0
    for term in blacklist_terms:
        results = cursor.execute(f'SELECT id, file FROM jobs WHERE title LIKE \'%{term}%\' AND status=\'new\'').fetchall()
        for result in results:
            os.remove(f'job_descriptions/{result[1]}')
            cursor.execute(f"UPDATE jobs SET status='easy_filter' WHERE id={result[0]}")
            connection.commit()
            counter += 1
    print(f'Easy filter caught {counter} jobs')


if __name__ == '__main__':
    main()
