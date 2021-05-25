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
```yaml
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
```cron
0 */2 * * * /path/to/craigslist-renew.py /path/to/config.yml
```

You can only renew a post so many times before it expires, so to get notified about expired posts, make sure you have configured the `postings` parameter in your configuration and add the following (daily) cronjob:
```cron
0 21 * * * /path/to/craigslist-renew.py --expired /path/to/config.yml
```

## Docker Image

[![dockeri.co](https://dockeri.co/image/jsetton/craigslist-renew)](https://hub.docker.com/r/jsetton/craigslist-renew).

### Supported tags

By default, the chromedriver package is included as local webdriver. If you rather use a [Selenium Grid](https://www.selenium.dev/docs/site/en/grid/) server instead, use the `remote` tag. If going with the latter, make sure to specify the remote url in the config file.

|       Tags        | Description              |
| :---------------: | ------------------------ |
| `latest`, `local` | Local webdriver support  |
|     `remote`      | Remote webdriver support |

### Run commands

Make sure that the configuration file `config.yml` is in the directory you are running the commands below or specify the proper directory path in the volume parameter. The log file path should be set to `/data/<logfile>` in the configuration file, if specified.

#### Renew posts
```bash
docker run --rm -v $(pwd):/data jsetton/craigslist-renew
```

#### Check expired posts
```bash
docker run --rm -v $(pwd):/data jsetton/craigslist-renew --expired
```

## Kubernetes CronJob

To deploy this script as a [Kubernetes CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)

### Create ConfMap

``` bash
kubectl create configmap craigslist-renew-config --from-file=config.yml
```

### Apply the Job

Adjust `kubernetes/cronjob.yaml` cron schedule, defaults to every odd day.

``` bash
kubectl apply -f kubernetes/cronjob.yaml
```
