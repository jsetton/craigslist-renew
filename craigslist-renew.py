#!/usr/bin/env python
# This script logs in to your craigslist account and renews all posts that can be renewed
# The script should be invoked with a config file in yaml format containing the following info:
# ---
# email: <craigslist login>
# password: <craigslist password>
# notify: <comma separated list of emails>


import asyncio
import logging
import re
import sys
from argparse import ArgumentParser, FileType, Namespace
from email.message import EmailMessage
from typing import Any, Literal

import aiosmtplib
import zendriver as zd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from yaml import safe_load, YAMLError
from zendriver import Browser, Tab
from zendriver.core.connection import ProtocolException

APP_DESCRIPTION = "Craigslist Automatic Renewal"
CRAIGSLIST_LOGIN_URL = "https://accounts.craigslist.org/login"

log = logging.getLogger(__name__)

config: dict[str, Any] = {}
browser: Browser | None = None
tab: Tab | None = None


async def check_expired() -> None:
    content = await tab.get_content()
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table", attrs={"class": "accthp_postings"})
    headers = ["status", "manage", "title", "area", "date", "id"]
    expired: list[str] = []

    if table:
        for row in table.find("tbody").find_all("tr"):
            cells = map(
                lambda cell: re.sub(r"\s+", " ", cell.text.strip()), row.find_all("td")
            )
            info = dict(zip(headers, cells))

            if "Active" in info["status"]:
                for posting in config.get("postings", []):
                    title = re.compile(re.escape(posting.get("title")), flags=re.I)
                    area = re.compile(posting.get("area", ""), flags=re.I)
                    if title.search(info["title"]) and area.search(info["area"]):
                        posting["active"] = True
    for posting in config.get("postings", []):
        if not posting.get("active"):
            expired.append(f'{posting.get("title")} ({posting.get("area")})')
    if expired:
        await notify(
            f"The following posts have expired:\n\n{chr(10).join(expired)}",
            subject="Craigslist Expired Posts",
        )


async def renew_posts() -> None:
    for page in range(1, 6):
        while True:
            try:
                renew = await tab.select('input[type="submit"][value="renew"]')
                
                form_action = renew.parent.get("action")
                post_id = renew.parent.parent.parent.get("data-postingid")
                post_link = await tab.select(f'a[href*="/{post_id}.html"]')
                post_title = " ".join(post_link.text.split())
                post_url = post_link.get("href")

                await renew.click()

                if await has_posting_renewed():
                    await notify(
                        f'Renewed "{post_title}" ({post_url})',
                        sendmail=not config.get("no_success_mail"),
                    )

                    if not config.get("renew_all"):
                        return
                else:
                    await notify(
                        f"Could not renew post - {form_action}",
                        level="error",
                    )
                    return

                await tab.back()
                await tab.wait_for_ready_state()
                await tab.reload()
            except asyncio.TimeoutError:
                break

        try:
            page_link = await tab.select(f'a[href*="filter_page={page + 1}"]')
            await page_link.click()
        except asyncio.TimeoutError:
            break


async def has_posting_renewed() -> bool:
    try:
        await tab.find("This posting has been renewed")
        return True
    except asyncio.TimeoutError:
        return False


async def notify(
    message: str,
    subject: str = APP_DESCRIPTION,
    level: Literal["debug", "info", "warning", "error", "critical"] = "info",
    sendmail: bool = True,
) -> None:
    getattr(log, level)(
        f'{config["email"]}: {message}' if config.get("email") else message
    )

    if sendmail and config.get("notify") and config.get("smtp"):
        email_to = config.get("notify")
        if not isinstance(email_to, str):
            log.error("'notify' config parameter must be string")
            return

        smtp = config.get("smtp")
        if not isinstance(smtp, dict):
            log.error("'smtp' config parameter must be map")
            return

        smtp_server = smtp.get("server")
        if not isinstance(smtp_server, str):
            log.error("'smtp.server' config parameter must be string")
            return

        email = EmailMessage()
        email.set_content(message)
        email["Subject"] = subject
        email["To"] = email_to
        email["From"] = config.get("from", "craigslist-renew@localhost")

        hostname, _, port = smtp_server.partition(":")

        await aiosmtplib.send(
            email,
            hostname=hostname,
            port=int(port) if port and port.isdigit() else 25,
            username=config["smtp"].get("username"),
            password=config["smtp"].get("password"),
        )


async def login() -> Tab:
    try:
        tab = await browser.get(CRAIGSLIST_LOGIN_URL)

        email = config.get("email")
        if not isinstance(email, str):
            raise ValueError("'email' config parameter must be a string")

        email_field = await tab.select("#inputEmailHandle")
        await email_field.send_keys(email)

        password = config.get("password")
        if not isinstance(password, str):
            raise ValueError("'password' config parameter must be a string")

        password_field = await tab.select("#inputPassword")
        await password_field.send_keys(password)

        submit = await tab.select("#login")
        await submit.click()

        await tab.wait_for_ready_state()

        if tab.url != f"{CRAIGSLIST_LOGIN_URL}/home":
            raise RuntimeError("Login failed")

        active_button = await tab.select('button.filterbtn[value="active"]')
        await active_button.click()

        return tab
    except asyncio.TimeoutError:
        raise RuntimeError("Unexpected login page format")
    except ProtocolException:
        raise RuntimeError("Could not open login page")


async def logout() -> None:
    try:
        if tab:
            logout_link = await tab.select('a[href*="/logout"]')
            await logout_link.click()
    except asyncio.TimeoutError:
        pass


async def launch_browser() -> Browser:
    browser_executable_path: str | None = None
    if config.get("browser"):
        if not isinstance(config["browser"], str):
            raise ValueError("'browser' config parameter must be a string")
        browser_executable_path = config["browser"]
    elif config.get("webdriver"):
        if not isinstance(config["webdriver"], str):
            raise ValueError("'webdriver' config parameter must be a string")
        if not config["webdriver"].startswith("http"):
            browser_executable_path = config["webdriver"]

    return await zd.start(
        headless=True,
        browser_executable_path=browser_executable_path,
        browser_args=[
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--window-size=1920,1080",
        ],
        sandbox=False,
        user_agent=UserAgent().chrome,
    )

async def close_browser() -> None:
    if browser:
        await browser.stop()

def init_logging() -> None:
    handlers: list[logging.Handler] = []

    if config.get("logfile"):
        handlers.append(logging.FileHandler(filename=config["logfile"]))

    if sys.stdin.isatty():
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s %(message)s",
        level=logging.INFO,
        handlers=handlers,
    )

    logging.getLogger("zendriver").setLevel(logging.WARNING)


def parse_args() -> Namespace:
    parser = ArgumentParser(description=APP_DESCRIPTION)
    parser.add_argument(
        "--expired",
        action="store_true",
        dest="check_expired",
        help="check expired posts",
    )
    parser.add_argument(
        "config",
        type=FileType("r"),
        help="config file",
    )
    return parser.parse_args()


async def main() -> None:
    global config, browser, tab
    try:
        args = parse_args()
        config = safe_load(args.config)
        init_logging()
        browser = await launch_browser()
        tab = await login()

        if args.check_expired:
            await check_expired()
        else:
            await renew_posts()

    except YAMLError as e:
        await notify("Invalid config YAML format", level="error")
        log.error(f"YAML error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        await notify(str(e), level="error")
        sys.exit(1)
    except Exception as e:
        await notify("Something went wrong. Please check the logs.", level="error")
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        await logout()
        await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
