# craigslist-renew

This is a simple python script that will auto-renew all your active Craigslist posts. It can also notify you when a post expires.

## Requirements

Python 3.10 or higher is required.

Use the python package manager to install dependencies:

```
pip install -r requirements.txt
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
#
# Optional parameters
#
# specify list of email recipients to notify
notify: <comma separated list of emails>
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
# specify chrome-based browser executable path (optional, defaults to auto-detecting chromium)
# when running in Docker, chromium is available at /usr/bin/chromium-browser
# note: 'webdriver' parameter is also accepted for backward compatibility
#browser: <path-to-browser>
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

[![Docker Hub](https://img.shields.io/docker/pulls/jsetton/craigslist-renew)](https://hub.docker.com/r/jsetton/craigslist-renew)

### Supported tags
| Tag | Description |
| :---: | --- |
| `latest` | Latest stable release |

> The `local` and `remote` tags are no longer supported. Please use `latest` instead.

### Environment Variables
| Variable | Default | Description |
| :---: | :---: | --- |
| `PUID` | Auto-detected from `/data` | User ID to run the script as |
| `PGID` | Auto-detected from `/data` | Group ID to run the script as |

> By default, the container will automatically match the ownership of your data directory. If the ownership cannot be determined, it will fall back to `1000:1000`. You can override this behavior by setting `PUID` and `PGID` explicitly. Note that running as root (`PUID=0` or `PGID=0`) is not supported.

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
