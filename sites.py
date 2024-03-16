import sqlite3
from collections import namedtuple
from typing import List

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from tqdm import tqdm

JobDetails = namedtuple('JobDetails', ['id', 'title', 'company'])


class Site:
    BASE_URL: str
    JOB_URL: str
    cursor: sqlite3.Cursor
    connection: sqlite3.Connection

    def download_new_jobs(self, query) -> None:
        raise NotImplemented

    def list_all_jobs(self, query) -> List[JobDetails]:
        page = 0
        jobs = []
        new_results = True
        with tqdm(total=1, desc='Search pages', unit=' page') as pbar:
            while new_results:
                page += 1
                this_page = self.get_jobs_from_page(page, query)
                jobs.extend(this_page)
                if len(this_page) == 0:
                    new_results = False
                else:
                    pbar.total = page + 1
                pbar.update()
        return jobs

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        raise NotImplemented

    def extract_job_info(self, job) -> JobDetails:
        raise NotImplemented

    def build_job_link(self, job_id) -> str:
        return self.JOB_URL.replace('%%ID%%', str(job_id))


class Seek(Site):
    def __init__(self, db_connection):
        self.BASE_URL = 'https://www.seek.com.au/'
        self.JOB_URL = 'https://www.seek.com.au/job/%%ID%%'

        if db_connection is not None:
            self.connection = db_connection
            self.cursor = db_connection.cursor()

    def download_new_jobs(self, query) -> None:
        print(f'Searching on Seek for "{query}"')
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
            response = requests.get(self.build_job_link(i[0]))
            soup = BeautifulSoup(response.text, features="html.parser")
            body: Tag = soup.find('div', attrs={'data-automation': 'jobAdDetails'})
            match = body.contents[0]

            # Removing the ' because it screws with db stuff
            i = JobDetails(i.id, i.title.replace("'", ""), i.company.replace("'", ""))
            file_name = f'{i[1]}-{i[2]}-{i[0]}.html'.replace('/', '_')
            with open('job_descriptions/' + file_name, 'w+') as f:
                try:
                    f.write(match.prettify())
                except UnicodeEncodeError:
                    continue
            self.cursor.execute(
                f"INSERT INTO jobs VALUES('{i.id}', '{i.title}', '{i.company}', '{file_name}', false, 'new', 'seek')")
            self.connection.commit()

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        response = requests.get(
            self.BASE_URL + f'{query}-jobs/in-Brisbane-CBD-&-Inner-Suburbs-Brisbane-QLD?page={page_number}')
        if response.status_code != 200:
            print('The response returned a non-200 status.')

        soup = BeautifulSoup(response.text, features="html.parser")
        matches = soup.find_all('a', attrs={'data-automation': 'jobTitle'})
        return [self.extract_job_info(x) for x in matches]

    def extract_job_info(self, job) -> JobDetails:
        link = job['href']
        job_id = link[link.rindex('/') + 1:link.index('?')]
        title = job.string
        company_field = job.parent.parent.parent.find('a', attrs={'data-automation': 'jobCompany'})
        if company_field is not None:
            company = company_field.string
        else:
            company = 'Private Advertiser'
        return JobDetails(job_id, title, company)


class Indeed(Site):
    def __init__(self, db_connection):
        self.BASE_URL = 'https://au.indeed.com/jobs?q='
        self.JOB_URL = 'https://au.indeed.com/viewjob?jk=%%ID%%'

        if db_connection is not None:
            self.connection = db_connection
            self.cursor = db_connection.cursor()

    def download_new_jobs(self, query) -> None:
        print(f'Searching on Indeed for "{query}"')
        indeed_jobs = self.list_all_jobs(query)

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        response = requests.get(
            self.BASE_URL + f'{query}&l=Brisbane+QLD&radius=10&start={(page_number - 1) * 10}',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0'})
        if response.status_code != 200:
            print('The response returned a non-200 status.')

        soup = BeautifulSoup(response.text, features="html.parser")
        matches = soup.find_all('a', attrs={'class': 'jcs-JobTitle css-jspxzf eu4oa1w0'})
        return [self.extract_job_info(x) for x in matches]
