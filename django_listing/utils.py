#
# Created : 2018-04-01
#
# @author: Eric Lapouyade
#
import copy
import pprint

pp = pprint.PrettyPrinter(indent=4)


def normalize_list(
    value, separator=",", transform=str.strip, default="", force_length=None
):
    if isinstance(value, str):
        value = list(map(transform, value.split(separator)))
    if force_length:
        length = len(value)
        if force_length < length:
            value = value[:force_length]
        elif force_length > length:
            value = value + [default] * (force_length - length)
    return value


def normalize_choices(choices, int_keys=False):
    normalized_choices = []
    if isinstance(choices, str):
        for c in choices.split(","):
            if ":" in c:
                normalized_choices.append(c.split(":", 1))
            else:
                normalized_choices.append([c, c])
    elif isinstance(choices, (tuple, list)):
        for c in choices:
            if isinstance(c, str):
                normalized_choices.append([c, c])
            elif isinstance(c, (tuple, list)):
                if len(c) == 1:
                    normalized_choices.append([c[0], c[0]])
                elif len(c) == 2:
                    normalized_choices.append(c)
    if int_keys:
        for c in normalized_choices:
            k = c[0]
            if isinstance(k, str):
                try:
                    c[0] = int(k)
                except ValueError:
                    pass
    return normalized_choices


def init_dicts_from_class(obj, attributes):
    for attr in attributes:
        val = getattr(obj, attr, None)
        if val is None:
            setattr(obj, attr, {})
        else:
            setattr(obj, attr, copy.deepcopy(val))


def pretty_format_querydict(qd):
    out = ""
    for k in sorted(qd.keys()):
        v = qd.getlist(k)
        if len(v) == 1:
            v = v[0]
        out += "'{k}' : {v}\n".format(k=k, v=repr(v))
    return out


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


class JsonDirect(str):
    pass


# TODO : create functions to add sum/min/max/avg columns to a sequence
