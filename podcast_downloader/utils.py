import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/5.37.36"
}

def extract_episode_number(title_str):
    """
    Extracts the episode number from a title string.
    Priority: #Number > Number at Start > Number at End.
    Returns 0 if no number is found in the expected patterns.
    """
    if not title_str:
        return 0
    match = re.search(r"^\s*?(\d+)|#(\d+)|(\d+)\s*$", title_str)
    if match:
        if match.group(2):
            return int(match.group(2))
        if match.group(1):
            return int(match.group(1))
        if match.group(3):
            return int(match.group(3))
    return 0