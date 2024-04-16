import os
from difflib import SequenceMatcher

import psycopg2
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm

from sites import Seek, Jora, Indeed

SEARCH_TERMS = ['programmer', 'computer-science', 'software-engineer', 'software-developer']


def main():
    connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
    connection.autocommit = True

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)

    sites = [Seek(connection), Jora(connection), Indeed(connection, driver)]
    for site in tqdm(sites, desc='Sites', unit='site'):
        for term in tqdm(SEARCH_TERMS, desc='Terms', unit='term', leave=False):
            site.download_new_jobs(term)

    mark_duplicates(connection)
    easy_filter(connection)


def mark_duplicates(connection):
    cursor = connection.cursor()

    cursor.execute("SELECT id, title, company FROM job_search WHERE status = 'new'")
    new_jobs = cursor.fetchall()

    cursor.execute("SELECT id, title, company FROM job_search")
    jobs = cursor.fetchall()

    duplicates = []
    for id_source, title_source, company_source in tqdm(new_jobs, desc='Checking for duplicates', unit='job'):
        temp_duplicates = []
        for id_target, title_target, company_target in tqdm(jobs, leave=False):
            if id_source == id_target:
                continue
            title_score = SequenceMatcher(None, title_source, title_target).ratio()
            company_score = SequenceMatcher(None, company_source, company_target).ratio()
            if title_score > 0.9 and company_score > 0.9:
                temp_duplicates.append(id_target)
        duplicates.append((id_source, temp_duplicates))
    duplicates = [x for x in duplicates if len(x[1]) != 0]
    for id_source, temp_duplicates in duplicates:
        cursor.execute(f"UPDATE job_search SET duplicate='{','.join([str(x) for x in temp_duplicates])}' WHERE id='{id_source}'")
    print('Duplicates found:', len(duplicates))


def easy_filter(connection):
    blacklist_terms = ['.net', 'senior', 'lead', 'architect', 'principal',
                       'director', 'business', 'manager', 'support',
                       'analyst', 'security', '2025', 'design', 'clinic',
                       'service', 'manage', 'coordinator', 'sale']
    cursor = connection.cursor()
    counter = 0
    for term in blacklist_terms:
        cursor.execute(f'SELECT id, file FROM job_search WHERE title LIKE \'%{term}%\' AND status=\'new\'')
        results = cursor.fetchall()
        for result in results:
            os.remove(f'job_descriptions/{result[1]}')
            cursor.execute(f"UPDATE job_search SET status='easy_filter' WHERE id='{result[0]}'")
            counter += 1
    print(f'Easy filter caught {counter} jobs')


if __name__ == '__main__':
    main()
