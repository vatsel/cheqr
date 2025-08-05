import dateparser
from datetime import datetime, timezone


def string_is_blank(s:str) -> bool:
    return not s or s.strip() == ""


def utc_now():
    return datetime.now(timezone.utc)


def parse_str_without_ai(date_str:str) -> datetime | None:
    """watch out for overwriting with Default information."""
    # Parse the string to a datetime object
    parsed_date = dateparser.parse(date_str)
    
    if parsed_date is None:
        return None

    return parsed_date  # Return just the date part