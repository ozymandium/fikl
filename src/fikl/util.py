"""
Common utilities
"""
from inspect import cleandoc
from markdown import markdown as html_from_md


def ensure_type(obj, t):
    """Ensure that an object is of a certain type"""
    if type(obj) is not t:
        raise TypeError("object {} is not of type {}".format(obj, t))


def html_from_doc(doc: str) -> str:
    """take an indented markdown string and convert it to html"""
    return html_from_md(cleandoc(doc), extensions=["extra"])
