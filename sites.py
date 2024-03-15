import re
import sqlite3
import os
from collections import defaultdict, namedtuple
from bs4.element import Tag
from typing_extensions import List, Tuple

import requests
from html2text import html2text
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

JobDetails = namedtuple('JobDetails', ['id', 'title', 'company'])

class Site:
    BASE_URL: str
    JOB_URL: str
    cursor: sqlite3.Cursor
    connection: sqlite3.Connection

    def __init__(self):
        raise NotImplemented

    def download_new_jobs(self, query) -> None:
        raise NotImplemented

    def list_all_jobs(self, query) -> List[JobDetails]:
        raise NotImplemented

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        raise NotImplemented

    def extract_job_info(self, job) -> JobDetails:
        raise NotImplemented


class Seek(Site):
    def __init__(self, db_connection):
        self.BASE_URL = 'https://www.seek.com.au/'
        self.JOB_URL = 'https://www.seek.com.au/job/'

        if db_connection is not None:
            self.connection = db_connection
            self.cursor = db_connection.cursor()

    def download_new_jobs(self, query) -> None:
        print(f'Searching for "{query}"')
        seek_jobs = self.list_all_jobs(query)
        remove_list = set()
        for i, job_source in enumerate(seek_jobs):
            for j, job_test in enumerate(seek_jobs):
                if i == j: continue
                if job_source.id == job_test.id:
                    if job_source not in remove_list:
                        remove_list.add(job_test)
        seek_jobs = [x for x in seek_jobs if x not in remove_list]

        result = self.cursor.execute('SELECT id FROM jobs').fetchall()
        old_job_ids = [x[0] for x in result]

        seek_jobs = [x for x in seek_jobs if int(x[0]) not in old_job_ids]

        for i in tqdm(seek_jobs, desc='Getting jobs', unit=' job'):
            response = requests.get(self.JOB_URL + i[0], verify=False)
            soup = BeautifulSoup(response.text, features="html.parser")
            body: Tag = soup.find('div', attrs={'data-automation': 'jobAdDetails'})
            match: Tag = body.contents[0]

            # Removing the ' because it screws with db stuff
            i = JobDetails(i.id, i.title.replace("'", ""), i.company.replace("'", ""))
            file_name = f'{i[1]}-{i[2]}-{i[0]}.html'.replace('/', '_')
            with open('job_descriptions/' + file_name, 'w+') as f:
                # Potential to turn the HTML into Markdown
                # text = html2text(str(match))
                try:
                    f.write(match.prettify())
                except UnicodeEncodeError as ignored:
                    continue
            self.cursor.execute(f"INSERT INTO jobs VALUES('{i.id}', '{i.title}', '{i.company}', '{file_name}', false, 'new', 'seek')")
            self.connection.commit()


    def list_all_jobs(self, query) -> List[JobDetails]:
        page = 0
        seek_jobs = []
        this_page = []
        new_results = True
        with tqdm(total=1, desc='Search pages', unit=' page') as pbar:
            while new_results:
                page += 1
                this_page = self.get_jobs_from_page(page, query)
                seek_jobs.extend(this_page)
                if len(this_page) == 0:
                    new_results = False
                else:
                    pbar.total = page + 1
                pbar.update()
        return seek_jobs

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        response = requests.get(self.BASE_URL + f'{query}-jobs/in-Brisbane-CBD-&-Inner-Suburbs-Brisbane-QLD?page={page_number}', verify=False)
        if response.status_code != 200:
            print('The response returned a non-200 status.')

        soup = BeautifulSoup(response.text, features="html.parser")
        matches = soup.find_all('a', attrs={'data-automation': 'jobTitle'})
        return [self.extract_job_info(x) for x in matches]

    def extract_job_info(self, job) -> JobDetails:
        link = job['href']
        id = link[link.rindex('/') + 1:link.index('?')]
        title = job.string
        company_field = job.parent.parent.parent.find('a', attrs={'data-automation': 'jobCompany'})
        if company_field is not None:
            company = company_field.string
        else:
            company = 'Private Advertiser'
        return JobDetails(id, title, company)
