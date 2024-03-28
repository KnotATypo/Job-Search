import os
import sqlite3
from difflib import SequenceMatcher

import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

from sites import Seek, Jora, Indeed

SEARCH_TERMS = ['programmer', 'computer-science', 'software-engineer', 'software-developer']


def main():
    connection = setup()

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)

    sites = [Seek(connection), Jora(connection), Indeed(connection, driver)]
    for site in tqdm(sites, desc='Sites', unit='site'):
        for term in tqdm(SEARCH_TERMS, desc='Terms', unit='term', leave=False):
            site.download_new_jobs(term)

    driver.close()

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
    new_jobs = cursor.execute("SELECT id, title, company FROM jobs WHERE status = 'new'").fetchall()
    jobs = cursor.execute("SELECT id, title, company FROM jobs WHERE status != 'new'").fetchall()
    duplicates = []
    for id_source, title_source, company_source in new_jobs:
        temp_duplicates = []
        for id_target, title_target, company_target in jobs:
            title_score = SequenceMatcher(None, title_source, title_target).ratio()
            company_score = SequenceMatcher(None, company_source, company_target).ratio()
            if title_score > 0.9 and company_score > 0.9:
                temp_duplicates.append(id_target)
        duplicates.append((id_source, temp_duplicates))
    duplicates = [x for x in duplicates if len(x[1]) != 0]
    for id_source, temp_duplicates in duplicates:
        cursor.execute(f"UPDATE jobs SET duplicate='{','.join([str(x) for x in temp_duplicates])}' WHERE id='{id_source}'")
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
            os.remove(f'job_descriptions/{result[1]}')
            cursor.execute(f"UPDATE jobs SET status='easy_filter' WHERE id='{result[0]}'")
            connection.commit()
            counter += 1
    print(f'Easy filter caught {counter} jobs')


if __name__ == '__main__':
    main()
