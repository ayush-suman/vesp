def get_key_index(k) -> tuple[str, int]:
    i = len(k) - 2
    while i >= 0:
        if k[i] == "#":
            try: return k[:i], int(k[i + 1:])
            except: raise KeyError(f"# in {k} should follow an integer")
        i -= 1

