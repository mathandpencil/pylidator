import logging

from six import string_types
from .constants import ERROR, WARN, LEVELS

logger = logging.getLogger(__name__)


class Error(dict):
    ERROR = ERROR
    WARN = WARN

    LEVELS = [ERROR, WARN]


class ErrorLedger(object):
    ERROR = ERROR
    WARN = WARN

    def __init__(self, default_object_data=None, logging=True):
        """
        `custom_field_name_mapper` is an optional callable that takes the field name and returns
            a verbose_name for the field.
        """
        self._errors = []
        self._is_valid = True
        self._default_object_data = default_object_data if default_object_data is not None else {}
        self._logging = logging
        self._already_logged = set()

    @staticmethod
    def create_error_object(message, level, object_data=None):
        if isinstance(message, dict):
            assert len(message) == 1, "Don't currently support multi key dicts inside lists."

            for field_name, error in message.items():
                error = "{}: {}".format(field_name, error)
                new_item = Error({"message": error, "field": field_name})
                break

        elif isinstance(message, string_types):
            new_item = Error({"message": message})

        else:
            raise ValueError("Message is required and must be a string or a dict: {}".format(message))

        new_item["level"] = level
        if object_data:
            new_item.update(object_data)

        return new_item

    def merge_with(self, other_ledger):
        assert isinstance(other_ledger, ErrorLedger)

        self._errors += other_ledger._errors
        self._is_valid = self._is_valid and other_ledger._is_valid
        self._already_logged = self._already_logged.union(other_ledger._already_logged)

    def add_message(self, message, level, object_data=None):
        new_item = self.create_error_object(message, level, object_data)
        new_item.update(self._default_object_data)
        self.add_object(new_item)

    def add_object(self, new_item_data):
        new_item = Error()
        new_item.update(self._default_object_data)
        new_item.update(new_item_data)

        new_item["level"]
        new_item["message"]

        if self._logging:
            log_message = "{} {}".format(new_item["level"], new_item["message"])
            # It is annoying when it writes the same msg a million times...
            if log_message not in self._already_logged:
                logger.debug(log_message)
                self._already_logged.add(log_message)

        self._errors.append(new_item)
        if new_item["level"] == self.ERROR:
            self._is_valid = False

    def get_full_results(self):
        return self._errors

    def get_error_messages(self):
        return list(unique_everseen([e["message"] for e in self._errors if e["level"] == e.ERROR]))

    def get_descriptive_error_messages(self):
        return list(["{} {}".format(e.get("description"), e["message"]) for e in self._errors if e["level"] == e.ERROR])

    def get_warning_messages(self):
        return list(unique_everseen([e["message"] for e in self._errors if e["level"] == e.WARN]))

    def get_errors(self):
        return [e for e in self._errors if e["level"] == e.ERROR]

    def get_warnings(self):
        return [e for e in self._errors if e["level"] == e.WARN]

    def is_valid(self):
        return self._is_valid

    def get_django_validation_formatted_errors(self):
        ret = {}
        for e in self._errors:
            field = e.get("field", "non_field_errors")
            level = e["level"]

            try:
                d = ret[level]
            except KeyError:
                d = ret[level] = {}

            try:
                d2 = d[field]
            except KeyError:
                d2 = d[field] = []

            prefixToRemove = e.get("verbose_name", "") + ": "
            if e["message"].startswith(prefixToRemove):
                d2.append(e["message"][len(prefixToRemove) :])
            else:
                d2.append(e["message"])

        return ret


def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    from itertools import filterfalse

    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element
