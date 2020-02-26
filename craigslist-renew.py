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
from mechanize import Browser, LinkNotFoundError
from random import shuffle
from smtplib import SMTP
from subprocess import Popen, PIPE
from yaml import safe_load

description = 'Craigslist Automatic Renewal'
url = 'https://accounts.craigslist.org/login'
#
browser = Browser()
config = {}
log = logging.getLogger(__name__)

# the config file can list postings that should currently be active. This is specified in the config as:
# postings:
#   - title: My Posting
#     area: nyc
#   - title: Another posting
#     area: nyc
def check_expired():
    soup = BeautifulSoup(browser.response().read(), 'html5lib')
    table = soup.find('table', attrs={'class': 'accthp_postings'})
    headers = ['status', 'manage', 'title', 'area', 'date', 'id']
    expired = []

    for row in table.find('tbody').find_all('tr'):
        cells = map(lambda cell: re.sub(r'\s+', ' ', cell.text.strip()), row.find_all('td'))
        info = dict(zip(headers, cells))

        if info['status'] == 'Active':
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
        for nr, form in enumerate(browser.forms()):
            for control in form.controls:
                if control.type == 'submit' and control.name == 'go' and control.value == 'renew':
                    # fetch posting link
                    post_id = form.action.split('/')[-1]
                    link = browser.find_link(url_regex='{}\.html$'.format(post_id))
                    # click the renew button
                    browser.select_form(nr=nr)
                    browser.submit()

                    # check posting has been renewed
                    if re.search(r'This posting has been renewed',
                                 browser.response().read().decode('utf-8')):
                        notify('Renewed "{}" ({})'.format(link.text, link.url),
                               sendmail=not config.get('no_success_mail'))
                        # only renew the first posting unless config renew_all setting enabled
                        if not config.get('renew_all'):
                            return
                    else:
                        notify('Could not renew post - {}'.format(form.action),
                               level='error')

                    # return to previous page
                    browser.back()
                    break

        # go to next page if link found
        try:
            browser.follow_link(text=str(page + 1))
        except LinkNotFoundError:
            return

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
    # define shuffle request headers order callback function
    def shuffle_headers(request, headers):
        items = list(headers.items())
        shuffle(items)
        for key, _ in items:
            headers.move_to_end(key)

    # open login url
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', UserAgent().random)]
    browser.finalize_request_headers = shuffle_headers
    browser.open(url)

    # submit login credentials form
    browser.select_form(nr=0)
    browser['inputEmailHandle'] = config['email']
    browser['inputPassword'] = config['password']
    browser.submit(id='login')

    # once in a while, Craigslist verifies the login via Captcha
    if browser.geturl() != '{}/home'.format(url):
        notify('Login failed - requires captcha', level='error');
        sys.exit(1);

    # filter active posts only
    browser.select_form(nr=0)
    browser.submit(label='active')

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

# parse command line arguments
def parse_args():
    parser = ArgumentParser(description=description)
    parser.add_argument(
        '--expired', action='store_true', dest='check_expired', help='check expired posts')
    parser.add_argument(
        'config', type=FileType('r'), help='config file')
    return parser.parse_args()


if __name__ == '__main__':
    try:
        args = parse_args()
        config = safe_load(args.config)
        # initialize logging
        init_logging()
        # log in with email and password
        login()

        # check for expired posts if expired flag was specified, otherwise renew posts
        if args.check_expired:
            check_expired()
        else:
            renew_posts()

    except KeyError as e:
        log.error('Parameter {} not defined in config file'.format(e))
        sys.exit(1)
    except Exception as e:
        log.error('Something went wrong: {}'.format(e))
        sys.exit(1)
