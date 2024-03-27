import asyncio
import re
import sqlite3
from collections import namedtuple
from typing import List

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from pyppeteer import launch
from tqdm import tqdm

JobDetails = namedtuple('JobDetails', ['id', 'title', 'company'])


class Site:
    BASE_URL: str
    JOB_URL: str
    site_string: str
    cursor: sqlite3.Cursor
    connection: sqlite3.Connection

    def download_new_jobs(self, query) -> None:
        print(f'Searching on {self.site_string} for "{query}"')
        jobs = self.list_all_jobs(query)
        jobs = self.remove_duplicates(jobs)

        if len(jobs) == 0:
            return
        for i in tqdm(jobs, desc='Getting jobs', unit='job'):
            # Removing the ' because it screws with db stuff
            i = JobDetails(i.id, i.title.replace("'", ""), i.company.replace("'", ""))
            file_name = f'{i[1]}-{i[2]}-{i[0]}.html'.replace('/', '_')
            with open('job_descriptions/' + file_name, 'w+') as f:
                try:
                    f.write(self.get_job_description(i[0]))
                except UnicodeEncodeError:
                    continue
            self.cursor.execute(
                f"INSERT INTO jobs VALUES('{i.id}', '{i.title}', '{i.company}', '{file_name}', null, 'new', '{self.site_string.lower()}')")
            self.connection.commit()

    def list_all_jobs(self, query) -> List[JobDetails]:
        page = 0
        jobs = []
        new_results = True

        fetchone = self.cursor.execute(f"SELECT pages FROM page_size WHERE site = '{self.site_string.lower()}' and search = '{query}'").fetchone()
        if fetchone is None:
            expected_pages = 1
        else:
            expected_pages = fetchone[0]

        with tqdm(total=expected_pages, desc='Search pages', unit='page') as pbar:
            while new_results:
                page += 1
                this_page = self.get_jobs_from_page(page, query)
                jobs.extend(this_page)
                if len(this_page) == 0:
                    new_results = False
                if page > expected_pages:
                    pbar.total += 1
                pbar.update()

        if expected_pages > 1:
            self.cursor.execute(f"UPDATE page_size SET pages = '{page}' WHERE site = '{self.site_string.lower()}' and search = '{query}'")
        else:
            self.cursor.execute(f"INSERT INTO page_size VALUES ('{self.site_string.lower()}', '{query}', '{page}')")
        self.connection.commit()

        return jobs

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        raise NotImplemented

    def extract_job_info(self, job) -> JobDetails:
        raise NotImplemented

    def build_job_link(self, job_id) -> str:
        return self.JOB_URL.replace('%%ID%%', str(job_id))

    def remove_duplicates(self, jobs):
        remove_list = set()
        for i, job_source in enumerate(jobs):
            for j, job_test in enumerate(jobs):
                if i == j: continue
                if job_source.id == job_test.id:
                    if job_source not in remove_list:
                        remove_list.add(job_test)
        jobs = [x for x in jobs if x not in remove_list]
        result = self.cursor.execute('SELECT id FROM jobs').fetchall()
        old_job_ids = [str(x[0]) for x in result]
        jobs = [x for x in jobs if str(x[0]) not in old_job_ids]
        return jobs

    def get_job_description(self, job_id) -> str | None:
        raise NotImplemented


class Seek(Site):
    def __init__(self, db_connection):
        self.BASE_URL = 'https://www.seek.com.au/'
        self.JOB_URL = 'https://www.seek.com.au/job/%%ID%%'
        self.site_string = 'Seek'

        if db_connection is not None:
            self.connection = db_connection
            self.cursor = db_connection.cursor()

    def get_job_description(self, job_id) -> str | None:
        response = requests.get(self.build_job_link(job_id))
        soup = BeautifulSoup(response.text, features="html.parser")
        body: Tag = soup.find('div', attrs={'data-automation': 'jobAdDetails'})
        if body is not None:
            return body.contents[0].prettify()
        else:
            return None

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


class Jora(Site):
    def __init__(self, db_connection):
        self.BASE_URL = 'https://au.jora.com/j?l=Brisbane+QLD&q='
        self.JOB_URL = 'https://au.jora.com/job/%%ID%%'
        self.site_string = 'Jora'

        if db_connection is not None:
            self.connection = db_connection
            self.cursor = db_connection.cursor()

    def get_job_description(self, job_id) -> str | None:
        loop = asyncio.get_event_loop()
        content = loop.run_until_complete(get(self.build_job_link(job_id)))
        soup = BeautifulSoup(content, features="html.parser")
        body: Tag = soup.find('div', attrs={'id': 'job-description-container'})
        if body is not None:
            return body.prettify()
        else:
            return None

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        loop = asyncio.get_event_loop()
        content = loop.run_until_complete(get(f"{self.BASE_URL}{query.replace('-', '+')}&p={page_number}"))

        soup = BeautifulSoup(content, features="html.parser")
        if soup.text.find('We have looked through all the results for you') != -1:
            return []
        last_page = int(re.findall(r'\d+', soup.find_all('div', 'search-results-count')[0].text)[-1])
        if page_number > last_page:
            return []
        matches = soup.find_all('a', attrs={'class': 'job-link -no-underline -desktop-only show-job-description'})
        matches = [self.extract_job_info(x) for x in matches]
        return matches

    def extract_job_info(self, job) -> JobDetails:
        link = job['href']
        job_id = link[link.rindex('/') + 1:link.index('?')]
        title = job.text
        company = job.parent.parent.parent.parent.find('span', attrs={'class', 'job-company'}).text
        return JobDetails(job_id, title, company)


async def get(link) -> str:
    browser = await launch()
    page = await browser.newPage()
    await page.goto(link)
    page_content = await page.content()
    await browser.close()
    return page_content
