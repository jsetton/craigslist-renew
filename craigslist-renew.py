#!/usr/bin/env python3
# This script logs in to your craigslist account and renews all posts that can be renewed
# The script should be invoked with a config file in yaml format containing the following info:
# ---
# email: <craigslist login>
# password: <craigslist password>
# notify: <comma separated list of emails>

import logging
import re
import sys
from argparse import ArgumentParser, FileType
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from fake_useragent import UserAgent
from random import shuffle
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from smtplib import SMTP
from subprocess import Popen, PIPE
from yaml import safe_load

description = 'Craigslist Automatic Renewal'
url = 'https://accounts.craigslist.org/login'
#
log = logging.getLogger(__name__)

# the config file can list postings that should currently be active. This is specified in the config as:
# postings:
#   - title: My Posting
#     area: nyc
#   - title: Another posting
#     area: nyc
def check_expired():
    soup = BeautifulSoup(driver.page_source, 'html5lib')
    table = soup.find('table', attrs={'class': 'accthp_postings'})
    headers = ['status', 'manage', 'title', 'area', 'date', 'id']
    expired = []

    for row in table.find('tbody').find_all('tr'):
        cells = map(lambda cell: re.sub(r'\s+', ' ', cell.text.strip()), row.find_all('td'))
        info = dict(zip(headers, cells))

        if 'Active' in info['status']:
            for posting in config.get('postings', []):
                # mark this posting as active if it matches one of the configured postings
                title = re.compile(re.escape(posting.get('title')), flags=re.I)
                area  = re.compile(posting.get('area', ''), flags=re.I)
                if title.search(info['title']) and area.search(info['area']):
                    posting['active'] = True

    for posting in config.get('postings', []):
        if not posting.get('active'):
            expired.append('{} ({})'.format(posting.get('title'), posting.get('area')))

    if expired:
        notify('The following posts have expired:\n\n{}'.format('\n'.join(expired)),
               subject='Craigslist post expired')

# renew posts
def renew_posts():
    # loop thru up to 5 pages
    for page in range(1, 6):
        # look for all listings with a renew button
        while True:
            try:
                # find next renew button element
                button = driver.find_element_by_xpath('//input[@type="submit" and @value="renew"]')
                # fetch posting link
                form_action = button.find_element_by_xpath('..').get_attribute('action')
                post_id = form_action.split('/')[-1]
                link = driver.find_element_by_xpath('//a[contains(@href, "/{}.html")]'.format(post_id))
                title = link.text
                url = link.get_attribute('href')
                # click the renew button
                button.click()

                # check posting has been renewed
                if has_posting_renewed():
                    notify('Renewed "{}" ({})'.format(title, url),
                           sendmail=not config.get('no_success_mail'))
                    # only renew the first posting unless config renew_all setting enabled
                    if not config.get('renew_all'):
                        return
                else:
                    notify('Could not renew post - {}'.format(form_action),
                           level='error')
                    return

                # return to previous refreshed page
                driver.back()
                driver.refresh()

            except NoSuchElementException:
                break

        # go to next page if link found
        try:
            driver.find_element_by_xpath('//a[contains(@href, "filter_page={}")]'.format(page + 1)).click()
        except NoSuchElementException:
            return

# determine if posting has been renewed
def has_posting_renewed():
    try:
        driver.find_element_by_xpath('//*[contains(text(), "This posting has been renewed")]')
        return True
    except NoSuchElementException:
        return False

# print message in interactive mode or send email when run from cron
def notify(message, subject=description, level='info', sendmail=True):
    # log message
    getattr(log, level)('{}: {}'.format(config['email'], message))

    # send mail if sendmail parameter is true and config notify settings defined
    if sendmail and config.get('notify'):
        # set email content
        email = MIMEText(message)
        email['Subject'] = subject
        email['To'] = config['notify']
        if config.get('from'):
            email['From'] = config['from']

        # send email via smtp server if config provided, otherwise via sendmail command
        if config.get('smtp'):
            # initialize smtp server object
            server = SMTP(config['smtp'].get('server', 'localhost'))
            # login smtp server if credentials provided
            if config['smtp'].get('username') and config['smtp'].get('password'):
                server.login(config['smtp']['username'], config['smtp']['password'])
            # send email
            server.sendmail(
                config.get('from', 'craigslist-renew@localhost'),
                config['notify'],
                email.as_string())
        else:
            # initialize process object
            process = Popen(['/usr/sbin/sendmail', '-t'], stdin=PIPE)
            # send email
            process.communicate(email.as_bytes())

# login and get active posts
def login():
    try:
        # open login url
        driver.get(url)
        # submit login credentials form
        driver.find_element_by_xpath('//*[@id="inputEmailHandle"]').send_keys(config['email'])
        driver.find_element_by_xpath('//*[@id="inputPassword"]').send_keys(config['password'])
        driver.find_element_by_xpath('//*[@id="login"]').click()

        # exit if login failed
        if driver.current_url != '{}/home'.format(url):
            notify('Login failed', level='error')
            sys.exit(1)

        # filter active posts only
        driver.find_element_by_xpath('//button[@class="filterbtn" and @value="active"]').click()

    except NoSuchElementException:
        return

# logout to avoid dangling sessions
def logout():
    try:
        driver.find_element_by_link_text('log out').click()
    except NoSuchElementException:
        return


# initialize logging
def init_logging():
    handlers = []
    # add file logging, if specified in config
    if config.get('logfile'):
        handlers.append(logging.FileHandler(filename=config['logfile']))
    # add console logging, if standard in connected to tty
    if sys.stdin.isatty():
        handlers.append(logging.StreamHandler(sys.stdout))
    # set logging config
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(message)s',
        level=logging.INFO,
        handlers=handlers)

# initialize webdriver
def init_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('disable-extensions')
    options.add_argument('no-sandbox')
    options.add_argument('window-size=1920,1080')
    options.add_argument('user-agent={}'.format(UserAgent().chrome))

    if not config.get('webdriver'):
        driver = webdriver.Chrome(
            options=options
        )
    elif not config['webdriver'].startswith('http'):
        driver = webdriver.Chrome(
            executable_path=config['webdriver'],
            options=options
        )
    else:
        driver = webdriver.Remote(
            command_executor=config['webdriver'],
            desired_capabilities=options.to_capabilities()
        )

    # set driver wait limit to 5 seconds
    driver.implicitly_wait(5)

    return driver

# parse command line arguments
def parse_args():
    parser = ArgumentParser(description=description)
    parser.add_argument(
        '--expired', action='store_true', dest='check_expired', help='check expired posts')
    parser.add_argument(
        'config', type=FileType('r'), help='config file')
    return parser.parse_args()


if __name__ == '__main__':
    global config, driver
    try:
        # parse command arguments
        args = parse_args()
        # load config file
        config = safe_load(args.config)
        # initialize webdriver
        driver = init_webdriver()
        # initialize logging
        init_logging()
        # log in with email and password
        login()

        # check for expired posts if expired flag was specified, otherwise renew posts
        if args.check_expired:
            check_expired()
        else:
            renew_posts()

        # Log out to avoid dangling sessions.
        logout()

    except KeyError as e:
        log.error('Parameter {} not defined in config file'.format(e))
        sys.exit(1)
    except Exception as e:
        log.error('Something went wrong: {}'.format(e))
        sys.exit(1)
