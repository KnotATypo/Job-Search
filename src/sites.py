import asyncio
import re
import sqlite3
from collections import namedtuple
from typing import List

import psycopg2
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from pyppeteer import launch
from selenium.webdriver.firefox.webdriver import WebDriver
from tqdm import tqdm

import util

HTML_PARSER = 'html.parser'

JobDetails = namedtuple('JobDetails', ['id', 'title', 'company'])


class Site:
    PAGE_URL: str
    JOB_URL: str
    SITE_STRING: str
    cursor: psycopg2.extensions.cursor
    connection: psycopg2.extensions.connection
    connection_lite: sqlite3.Connection
    cursor_lite: sqlite3.Cursor

    def __init__(self, page_url: str, job_url: str, site_string: str, connection: sqlite3) -> None:
        self.PAGE_URL = page_url
        self.JOB_URL = job_url
        self.SITE_STRING = site_string

        if connection is not None:
            self.connection = connection
            self.cursor = connection.cursor()

        self.connection_lite, self.cursor_lite = util.connect_sqlite()

    def download_new_jobs(self, query) -> None:
        fetchone = self.cursor_lite.execute(f"SELECT pages FROM page_size "
                                            f"WHERE site = '{self.SITE_STRING.lower()}' "
                                            f"and search = '{query}'").fetchone()
        if fetchone is None:
            expected_pages = 1
        else:
            expected_pages = fetchone[0]

        page = 0
        new_results = True
        with tqdm(total=expected_pages, desc=f'{self.SITE_STRING} - {query} pages', unit='page', leave=False) as pbar:
            while new_results:
                jobs = self.get_jobs_from_page(page, query)
                page += 1
                if len(jobs) == 0:
                    new_results = False
                else:
                    for job_id in self.remove_duplicates(jobs):
                        self.save_job(job_id)
                if page > expected_pages:
                    pbar.total += 1
                pbar.update()

        if expected_pages > 1:
            self.cursor_lite.execute(f"UPDATE page_size SET pages = '{page}' "
                                     f"WHERE site = '{self.SITE_STRING.lower()}' and search = '{query}'")
        else:
            self.cursor_lite.execute(f"INSERT INTO page_size VALUES ('{self.SITE_STRING.lower()}', '{query}', '{page}')")
        self.connection_lite.commit()

    def save_job(self, job: JobDetails) -> None:
        # Removing the ' because it screws with db stuff
        job = JobDetails(job.id, job.title.replace("'", ""), job.company.replace("'", ""))
        file_name = f'{job[1]}-{job[2]}-{job[0]}.html'.replace('/', '_')

        # Idk why but seek will sometimes give me duplicate ID's
        self.cursor.execute(f"INSERT INTO job_search VALUES("
                            f"'{str(job.id)}', "
                            f"'{job.title}', "
                            f"'{job.company}', "
                            f"'{file_name}', "
                            f"null, "
                            f"'new', "
                            f"'{self.SITE_STRING.lower()}'"
                            f")")

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        raise NotImplementedError

    def extract_job_info(self, job) -> JobDetails:
        raise NotImplementedError

    def build_job_link(self, job_id) -> str:
        return self.JOB_URL.replace('%%ID%%', str(job_id))

    def build_page_link(self, query, page_number):
        return self.PAGE_URL.replace('%%QUERY%%', str(query)).replace('%%PAGE%%', str(page_number))

    def remove_duplicates(self, jobs):
        self.cursor.execute('SELECT id FROM job_search')
        result = self.cursor.fetchall()
        old_job_ids = [str(x[0]) for x in result]
        jobs = [x for x in jobs if str(x[0]) not in old_job_ids]
        return jobs

    def get_job_description(self, job_id) -> str | None:
        raise NotImplementedError


class Seek(Site):
    def __init__(self, db_connection):
        super().__init__(
            'https://www.seek.com.au/%%QUERY%%-jobs/in-Brisbane-CBD-&-Inner-Suburbs-Brisbane-QLD?page=%%PAGE%%',
            'https://www.seek.com.au/job/%%ID%%',
            'Seek',
            db_connection
        )

    def get_job_description(self, job_id) -> str | None:
        response = requests.get(self.build_job_link(job_id))
        soup = BeautifulSoup(response.text, features=HTML_PARSER)
        body: Tag = soup.find('div', attrs={'data-automation': 'jobAdDetails'})
        if body is not None:
            return body.contents[0].prettify()
        else:
            return None

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        response = requests.get(self.build_page_link(query, page_number))
        if response.status_code != 200:
            print('The response returned a non-200 status.')

        soup = BeautifulSoup(response.text, features=HTML_PARSER)
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
    browser: WebDriver

    def __init__(self, db_connection, browser):
        super().__init__(
            'https://au.jora.com/j?l=Brisbane+QLD&q=%%QUERY%%&p=%%PAGE%%',
            'https://au.jora.com/job/%%ID%%',
            'Jora',
            db_connection
        )
        self.browser = browser

    def get_job_description(self, job_id) -> str | None:
        self.browser.get(self.build_job_link(job_id))
        soup = BeautifulSoup(self.browser.page_source, features=HTML_PARSER)
        # soup = BeautifulSoup(content, features=HTML_PARSER)
        body: Tag = soup.find('div', attrs={'id': 'job-description-container'})
        if body is not None:
            return body.prettify()
        else:
            return None

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        loop = asyncio.get_event_loop()
        content = loop.run_until_complete(get(self.build_page_link(query.replace('-', '+'), page_number)))

        soup = BeautifulSoup(content, features=HTML_PARSER)
        if soup.text.find('We have looked through all the results for you') != -1:
            return []
        last_page = int(re.findall(r'\d+', soup.find_all('div', 'search-results-page-number')[0].text)[-1])
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


class Indeed(Site):
    browser: WebDriver

    def __init__(self, db_connection, browser):
        super().__init__(
            'https://au.indeed.com/jobs?q=%%QUERY%%&l=Brisbane+QLD&radius=10&start=%%PAGE%%',
            'https://au.indeed.com/viewjob?jk=%%ID%%',
            'Indeed',
            db_connection
        )
        self.browser = browser

    def get_job_description(self, job_id) -> str | None:
        self.browser.get(self.build_job_link(job_id))
        soup = BeautifulSoup(self.browser.page_source, features=HTML_PARSER)
        body: Tag = soup.find('div', attrs={'class': 'jobsearch-JobComponent-description'})
        if body is not None:
            return body.prettify()
        else:
            return None

    def get_jobs_from_page(self, page_number, query) -> List[JobDetails]:
        self.browser.get(self.build_page_link(query.replace('-', '+'), page_number * 10))
        content = self.browser.page_source
        soup = BeautifulSoup(content, features=HTML_PARSER)

        result = soup.find('a', attrs={'data-testid': 'pagination-page-current'})
        if result is None or int(result.text) <= page_number:
            return []

        matches = soup.find_all("td", {"class": "resultContent"})
        return [self.extract_job_info(x) for x in matches]

    def extract_job_info(self, job) -> JobDetails:
        job_id = job.find('a')['id']
        job_id = job_id[job_id.index('_') + 1:]
        title = job.find('a').text
        company = job.find('span', {'data-testid': 'company-name'}).text

        return JobDetails(job_id, title, company)


async def get(link) -> str:
    browser = await launch()
    page = await browser.newPage()
    await page.goto(link)
    page_content = await page.content()
    await browser.close()
    return page_content
