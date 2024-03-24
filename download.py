import os
import sqlite3
from difflib import SequenceMatcher

import requests
from urllib3.exceptions import InsecureRequestWarning

from sites import Seek, Jora

SEARCH_TERMS = ['programmer', 'computer-science', 'software-engineer', 'software-developer']


def main():
    connection = setup()

    sites = [Seek(connection), Jora(connection)]
    for site in sites:
        for term in SEARCH_TERMS:
            site.download_new_jobs(term)

    mark_duplicates(connection)
    easy_filter(connection)


def setup():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    cursor.execute('CREATE TABLE IF NOT EXISTS '
                   'jobs('
                   'id STRING UNIQUE, '
                   'title STRING, '
                   'company STRING, '
                   'file STRING, '
                   'duplicate BOOLEAN, '
                   'status STRING, '
                   'site STRING'
                   ')')
    if not os.path.exists('job_descriptions'):
        os.mkdir('job_descriptions')

    return conn


def mark_duplicates(connection):
    cursor = connection.cursor()
    new_jobs = cursor.execute("SELECT id, title, company FROM jobs WHERE status = 'new'")
    jobs = cursor.execute("SELECT id, title, company FROM jobs")
    duplicates = set()
    for i, (id_source, title_source, company_source) in enumerate(new_jobs):
        for j, (id_target, title_target, company_target) in enumerate(jobs):
            if i == j: continue
            title_score = SequenceMatcher(None, title_source, title_target).ratio()
            company_score = SequenceMatcher(None, company_source, company_target).ratio()
            if (title_score + company_score) / 2 > 0.98:
                duplicates.add(id_source)
                duplicates.add(id_target)
    for id in duplicates:
        cursor.execute(f"UPDATE jobs SET duplicate=true WHERE id='{id}'")
        connection.commit()
    print('Duplicates found:', len(duplicates))


def easy_filter(connection):
    blacklist_terms = ['.net', 'senior', 'lead', 'architect', 'principal',
                       'graduate', 'director', 'business', 'manager', 'support',
                       'analyst', 'security']
    cursor = connection.cursor()
    counter = 0
    for term in blacklist_terms:
        results = cursor.execute(
            f'SELECT id, file FROM jobs WHERE title LIKE \'%{term}%\' AND status=\'new\'').fetchall()
        for result in results:
            try:
                os.remove(f'job_descriptions/{result[1]}')
            except FileNotFoundError:
                pass
            cursor.execute(f"UPDATE jobs SET status='easy_filter' WHERE id='{result[0]}'")
            connection.commit()
            counter += 1
    print(f'Easy filter caught {counter} jobs')


if __name__ == '__main__':
    main()
