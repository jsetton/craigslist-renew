# craigslist-renew

This is a simple python script that will auto-renew all your active Craigslist posts. It can also notify you when a post expires.

## Requirements

This project depends on the following python modules:

* `beautifulsoup4`
* `html5lib`
* `PyYAML`
* `selenium`

Use the python package manager to install them:

```
pip3 install -r requirements.txt
```

## Usage

Create a yaml config file with the following content:
```
---
#
# Required parameters
#
email: <craigslist login>
password: <craigslist password>
notify: <comma separated list of emails>
#
# Optional parameters
#
# specify sender email address
from: <sender email address>
# specify smtp server settings (defaults to using sendmail command if omitted)
smtp:
  server: <host:port>
  username: <mail username>
  password: <mail password>
# set to 1 to suppress notification emails on renewal
no_success_mail: <1|0>
# set to 1 to renew all posts available for renewal
# By default, only the first expired post gets renewed on each run
renew_all: <1|0>
# specify path for logging actions taken
logfile: <path-to-logfile>
# specify selenium webdriver local path or remote url (defaults to using chromedriver in local path if omitted)
webdriver: <path-to-webdriver>
# specify the list of your current postings for expiration notifications
postings:
  - title: My post
    area: nyc
  - title: Another post
    area: nyc
```

Then just schedule the script in cron to run at the schedule you want. Depending on the category and location, craigslist posts can be renewed about once every few days, so running the script every few hours should be more than sufficient:
```
0 */2 * * * /path/to/craigslist-renew.py /path/to/config.yml
```

You can only renew a post so many times before it expires, so to get notified about expired posts, make sure you have configured the `postings` parameter in your configuration and add the following (daily) cronjob:
```
0 21 * * * /path/to/craigslist-renew.py --expired /path/to/config.yml
```

## Docker

To avoid installing a python environment with all its dependencies you can run this script in a Docker container.

### Build image

By default, the chromedriver package is included as local webdriver. If you rather use a [Selenium Grid](https://www.selenium.dev/docs/site/en/grid/) server instead, that package can be excluded using the `LOCAL_WEBDRIVER` docker build argument. If going with the latter, make sure to specify the remote url in the config file.

#### Local webdriver support build (Default)
```
docker build -t craigslist-renew .
```

#### Remote webdriver support build
```
docker build -t craigslist-renew --build-arg LOCAL_WEBDRIVER=no .
```

### Run commands

Make sure that the configuration file `config.xml` is in the directory you are running the commands below or specify the proper directory path in the volume parameter. The log file path should be set to `/data/<logfile>` in the configuration file, if specified.

#### Renew posts
```
docker run --rm -v $(pwd):/data craigslist-renew
```

#### Check expired posts
```
docker run --rm -v $(pwd):/data craigslist-renew --expired
```
