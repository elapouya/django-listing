#
# Created : 2018-02-10
#
# @author: Eric Lapouyade
#

from django.utils.safestring import mark_safe

__all__ = ["HTMLAttributes"]


class HTMLAttributes(dict):
    def __init__(self, *args, **kwargs):
        # remove starting underscore to be able to use '_class'
        # instead of 'class' in kwargs (reserved keyword)
        if "_class" in kwargs:
            kwargs["class"] = kwargs.pop("_class")
        super().__init__(*args, **kwargs)

    def add(self, attr, value):
        if value is not None:
            if attr not in self:
                s = set()
            else:
                if attr == "style":
                    s = set(self[attr].split(";"))
                else:
                    s = set(self[attr].split())
            if isinstance(value, set):
                s.update(value)
            else:
                s.add(value)
            if attr == "style":
                self[attr] = (";".join(s)).strip()
            else:
                self[attr] = (" ".join(s)).strip()

    def remove(self, attr, value):
        if value is not None:
            if attr not in self:
                s = set()
            else:
                if attr == "style":
                    s = set(self[attr].split(";"))
                else:
                    s = set(self[attr].split())
            if isinstance(value, set):
                s -= value
            else:
                s -= set([value])  # do not use remove() to avoid KeyError
            if attr == "style":
                self[attr] = (";".join(s)).strip()
            else:
                self[attr] = (" ".join(s)).strip()

    def set(self, attr, value=None):
        self[attr] = value

    def __setattr__(self, attr, value):
        self[attr] = value

    def update(self, *args, **kwargs):
        # remove starting underscore to be able to use '_class'
        # instead of 'class' in kwargs (reserved keyword)
        if "_class" in kwargs:
            kwargs["class"] = kwargs.pop("_class")
        super().update(*args, **kwargs)

    def copy(self):
        return HTMLAttributes(self)

    def __str__(self):
        out = " ".join(
            [(k if v is None else '{}="{}"'.format(k, v)) for k, v in self.items()]
        )
        if out:
            out = " " + out
        return mark_safe(out)
