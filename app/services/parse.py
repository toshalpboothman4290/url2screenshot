import re, json

def parse_shot_args(text: str) -> str:
    """
    Parse flags from user input and return JSON string
    Recognized flags:
      --mobile, --desktop
      --full, --slice
      --pdf
      --slow (alias for --delay=7000)
      --delay=N  (milliseconds)
    """
    t = text or ""
    flags = {
        "mobile": "--mobile" in t,
        "desktop": "--desktop" in t,
        "full": "--full" in t,
        "slice": "--slice" in t,
        "pdf": "--pdf" in t,
    }

    # Delay handling
    m = re.search(r"--delay\s*=\s*(\d+)", t)
    if m:
        flags["delay_ms"] = int(m.group(1))
    elif "--slow" in t:
        flags["delay_ms"] = 7000

    # Default to mobile if neither mobile nor desktop specified
    if not flags["mobile"] and not flags["desktop"]:
        flags["mobile"] = True

    return json.dumps(flags, ensure_ascii=False)
