"""Address parsing helpers."""

import re


def parse_address_value(token, label_map=None):
    """Parse an address token (hex/decimal/label) into an integer."""
    if not token:
        raise ValueError("Empty address token")

    token = token.strip()
    if label_map:
        upper_map = {name.upper(): addr for name, addr in label_map.items()}
        if token.upper() in upper_map:
            return upper_map[token.upper()]

    token_upper = token.upper()
    try:
        if token_upper.startswith("0X"):
            return int(token_upper, 16)
        if token_upper.endswith("H"):
            return int(token_upper[:-1], 16)
        if token_upper.endswith("D"):
            return int(token_upper[:-1], 10)
        if re.fullmatch(r"[0-9A-F]+", token_upper):
            return int(token_upper, 16)
        if re.fullmatch(r"\d+", token_upper):
            return int(token_upper)
    except ValueError:
        pass
    raise ValueError(f"Unable to parse address '{token}'")
