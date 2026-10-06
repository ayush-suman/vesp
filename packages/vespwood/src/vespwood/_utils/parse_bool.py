def parse_bool(value):
    clean_val = value.strip().lower()
    if clean_val in ("yes", "true", "t", "1", "y"):
        return True
    elif clean_val in ("no", "false", "f", "0", "n"):
        return False
    else:
        raise ValueError(f"Given value {value} cannot be parsed to bool")