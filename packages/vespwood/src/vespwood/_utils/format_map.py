import string

from .get_arg import get_arg


def format_map(fmt, mapping):
    f = string.Formatter()
    out = []
    for literal, field, spec, conv in f.parse(fmt):
        out.append(literal)
        if field is None:
            continue
        param = field.strip() if "." not in field else field.strip().split(".", 1)
        if param in mapping:
            obj = get_arg(mapping, field)
            if conv:
                obj = f.convert_field(obj, conv)
            out.append(f.format_field(obj, spec))
        else:
            ph = '{' + field
            if conv:
                ph += '!' + conv
            if spec:
                ph += ':' + spec
            out.append(ph + '}')
    return ''.join(out)