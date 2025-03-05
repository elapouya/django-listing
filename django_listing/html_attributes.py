#
# Created : 2018-02-10
#
# @author: Eric Lapouyade
#

from django.utils.safestring import mark_safe

__all__ = ["HTMLAttributes", "Tag", "Html"]


class HTMLAttributes(dict):
    def __init__(self, *args, **kwargs):
        # remove starting underscore to be able to use '_class'
        # instead of 'class' in kwargs (reserved keyword)
        if "_class" in kwargs:
            kwargs["class"] = kwargs.pop("_class")
        super().__init__(*args, **kwargs)

    def add(self, attr, value):
        if value is not None:
            if isinstance(value, int):
                value = str(value)
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
                # use str to consume lazy strings
                self[attr] = (";".join(map(str, s))).strip()
            else:
                # use str to consume lazy strings
                self[attr] = (" ".join(map(str, s))).strip()

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


class Tag:
    def __init__(self, tag, text, **kwargs):
        """If named argument begins by a "_" replace them by a "-"
        this is useful because, "-" cannot be used in a name in python.
        This is also useful to use class which is reserved : use "_class" instead.
        """
        attributes = {}
        for k, v in kwargs.items():
            if k.startswith("_"):
                k = k.replace("_", "-")[1:]
            attributes[k] = v
        self.tag = tag
        self.text = text
        self.attributes = attributes

    def __str__(self):
        attributes_html = " ".join(f'{k}="{v}"' for k, v in self.attributes.items())
        return mark_safe(f"<{self.tag} {attributes_html}>{self.text}</{self.tag}>")


class Html:
    def __init__(self, html):
        self.html = html

    def __str__(self):
        return mark_safe(self.html)
