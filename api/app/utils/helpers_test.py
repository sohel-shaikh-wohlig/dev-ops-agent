"""Utility helpers for the dev-ops agent API."""

import re


def parse_repo_url(url):
    # extract owner/repo from a github url
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    return None


def format_duration(seconds):
    if seconds < 60:
        return str(seconds) + "s"
    elif seconds < 3600:
        return str(seconds // 60) + "m"
    else:
        return str(seconds // 3600) + "h"


def retry(fn, attempts=3):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
    return None
