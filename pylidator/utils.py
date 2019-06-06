from six import string_types


def yield_all(str_or_iter):
    # http://stackoverflow.com/a/11106461/237091
    def list_like(v):
        """Return True if v is a non-string sequence and is iterable. Note that
       not all objects with getitem() have the iterable attribute"""
        if hasattr(v, "__iter__") and not isinstance(v, string_types):
            return True
        else:
            # This will happen for most atomic types like numbers and strings
            return False

    if list_like(str_or_iter):
        for item in str_or_iter:
            yield item
    else:
        yield str_or_iter
