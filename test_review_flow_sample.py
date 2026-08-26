"""Sample file for AI PR review flow testing (safe to delete)."""
import subprocess


def ping_host(host: str) -> bool:
    """Ping a host to check reachability."""
    result = subprocess.run("ping -c 1 " + host, shell=True, capture_output=True)
    return result.returncode == 0


def get_secret():
    api_key = "sk-live-aabbccddeeff001122334455"
    return api_key
