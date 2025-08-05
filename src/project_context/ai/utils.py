from ..logging.service import setup_logger


def extract_json_from_text(text:str) -> str:
    logger = setup_logger()

    """find curly brackets"""
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace == -1 or last_brace == -1:
        logger.debug(f"Couldn't find JSON data via brackets positions, first brace @ {first_brace}"
                    f" last brace @ {last_brace}")
        return ""

    if first_brace >= last_brace:
        raise ValueError(f"unexpected earlier position of last brace @ {last_brace}"
                         f"before first brace @ {first_brace}")

    # passed all checks, return
    return text[first_brace:last_brace + 1]
    