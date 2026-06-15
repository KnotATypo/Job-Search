import atexit
import email
import imaplib
import re
import time
from contextlib import contextmanager
from email.header import decode_header
from queue import Queue

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

from job_search.model import User
from job_search.utilities.logger import logger

load_dotenv()


def get_page_soup(link: str) -> BeautifulSoup:
    """
    Returns a BeautifulSoup object for the given URL

    link -- The URL to get the page from
    """
    with driver_pool.provide() as slot:
        driver = slot.driver
        driver.get(link)
        content = driver.page_source
        soup = BeautifulSoup(content, features="html.parser")
    return soup


def seek_login(user: User, slot: DriverSlot):
    driver = slot.driver
    driver.get("https://www.seek.com")
    register_text = driver.find_element(By.CSS_SELECTOR, 'span[data-automation="register-link"]')
    register_text.find_element(By.CSS_SELECTOR, "a").click()
    try:
        driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys(user.email)
    except StaleElementReferenceException:
        driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys(user.email)
    driver.find_element(By.CSS_SELECTOR, 'button[data-cy="register"]').click()
    code_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="verification input"]')
    time.sleep(5)
    code = get_seek_code(user.email, user.email_password)
    code_input.send_keys(code)
    try:
        # Check that the code isn't invalid. If invalid, try to get code 2 more times
        time.sleep(2)
        for _ in range(2):
            alert = driver.find_element(By.CSS_SELECTOR, 'div[role="alert"]')
            if alert.text == "Invalid code. Try again or click resend below.":
                logger.warn("Invalid 2FA code, trying again")
                code_input.send_keys(Keys.BACKSPACE * 6)
                code = get_seek_code(user.email, user.email_password)
                code_input.send_keys(code)
            else:
                time.sleep(5)
    except NoSuchElementException:
        slot.seek_loggedin = True
        logger.debug("Successfully logged in")


def get_seek_code(email_address: str, password: str) -> str:
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(email_address, password)

    auth_code = ""
    while auth_code == "":
        imap.select("INBOX")
        _, search_data = imap.search(None, "UNSEEN")
        ids = search_data[0].split()[-3:]

        for raw_id in reversed(ids):
            msg_id = raw_id.decode()
            # Use BODY.PEEK[] to avoid marking the message as seen on fetch
            _, msg = imap.fetch(msg_id, "(BODY.PEEK[])")
            if msg[0] is None:
                continue
            msg = email.message_from_bytes(msg[0][1])

            subject, _ = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                continue

            logger.debug(f"Email {msg_id}: {subject}")
            if re.match(r"\d{6} is your code for SEEK", subject) is not None:
                auth_code = subject[:6]
                imap.store(msg_id, "+FLAGS", "\\Seen")
                imap.store(msg_id, "+FLAGS", "\\Deleted")
                break

    imap.close()
    imap.logout()

    return auth_code


def linkedin_login(user: User, slot: DriverSlot):
    while not slot.linkedin_loggedin:
        driver = slot.driver
        driver.get("https://au.linkedin.com/jobs")
        username_element = driver.find_element(By.CSS_SELECTOR, 'input[id="session_key"]')
        if username_element is None:
            slot.replace()
            continue

        username_element.send_keys(user.email)
        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(user.linkedin_password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(1)

        try:
            if driver.find_element(By.TAG_NAME, "h1").text == "Let’s do a quick security check":
                slot.replace()
        except NoSuchElementException:
            slot.linkedin_loggedin = True


class DriverSlot:
    driver: WebDriver
    seek_loggedin: bool
    linkedin_loggedin: bool

    def __init__(self):
        self.new_driver()
        self.seek_loggedin = False
        self.linkedin_loggedin = False

    def replace(self):
        self.driver.quit()
        self.seek_loggedin = False
        self.linkedin_loggedin = False
        self.new_driver()

    def new_driver(self):
        options = Options()
        options.add_argument("--headless")

        # Flag needed to run in Docker
        options.add_argument("--no-sandbox")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=options)

        # noinspection PyTypeChecker
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        self.driver.implicitly_wait(5)


class DriverPool:
    pool: Queue[DriverSlot] = Queue()

    def __init__(self):
        self.pool.put(DriverSlot())

    @contextmanager
    def provide(self):
        driver = self.pool.get()
        try:
            yield driver
        finally:
            self.pool.put(driver)

    def quit_all(self):
        while not self.pool.empty():
            self.pool.get().driver.quit()


driver_pool = DriverPool()
atexit.register(lambda: driver_pool.quit_all())
