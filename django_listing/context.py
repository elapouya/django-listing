#
# Created : 2018-02-10
#
# @author: Eric Lapouyade
#

import pprint

pp = pprint.PrettyPrinter(indent=4)
import types

__all__ = ["RenderContext"]


def isgenerator(arg):
    return isinstance(arg, types.GeneratorType)


# Simplistic context object : just a dict accessible with attribute notation
class RenderContext(dict):
    def __init__(self, *args, **kwargs):
        """
        If we're initialized with a dict, make sure we turn all the
        subdicts into Dicts as well.
        """
        for arg in args:
            if not arg:
                continue
            elif isinstance(arg, dict):
                for key, val in arg.items():
                    self[key] = val
            elif isinstance(arg, tuple) and (not isinstance(arg[0], tuple)):
                self[arg[0]] = arg[1]
            elif isinstance(arg, (list, tuple)) or isgenerator(arg):
                for key, val in arg:
                    self[key] = val
            # other types of postionnal arguments are not injected into the context

        for key, val in kwargs.items():
            self[key] = val

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value
