#
# Created : 2018-04-01
#
# @author: Eric Lapouyade
#
import copy
import pprint
from datetime import datetime, date

pp = pprint.PrettyPrinter(indent=4)


def normalize_list(
    value, separator=",", transform=str.strip, default="", force_length=None
):
    if isinstance(value, str):
        value = list(map(transform, value.split(separator)))
    elif isinstance(value, tuple):
        value = list(value)
    if force_length:
        length = len(value)
        if force_length < length:
            value = value[:force_length]
        elif force_length > length:
            value += [default] * (force_length - length)
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


def to_js_timestamp(dt_obj):
    """
    Convert Python date or datetime object to JavaScript timestamp (milliseconds)

    Args:
        dt_obj: date or datetime object

    Returns:
        int: JavaScript timestamp in milliseconds
    """
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        # Convert date to datetime at midnight
        dt_obj = datetime.combine(dt_obj, datetime.min.time())

    return int(dt_obj.timestamp() * 1000)


class FastAttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def setattr_to_object(self, obj):
        # Important to loop here as for Django model object it is mandatory
        for k, v in self.items():
            setattr(obj, k, v)

    def map_to_object(self, obj):
        obj.__dict__.update(self)


class JsonDirect(str):
    pass


class NotPresent:
    pass


NOT_PRESENT = NotPresent()
