from . import messages
from .utils import yield_all


def any_field_must_be_set(obj, attr, errors):
    """
    Call this method from a `pylidator.validator` to check that at least one of the attributes in `attr` are not None.

    Will add validation messages to `errors` if problems found.

    `obj`  object to test
    `attr` string or iterable of strings to specify attributes to test
    `errors` result list to add any validation messages
    """

    if isinstance(attr, basestring):
        field_must_be_set(obj, attr, errors)
    else:
        for item in attr:
            val = getattr(obj, item)
            if val is not None:
                return

        # All are None, so all get errors.
        errors.append({tuple(attr): messages.ANY_FIELD_IS_REQUIRED})


def field_must_be_set(obj, attr, errors):
    """
    Call this method from a `pylidator.validator` to check that all attributes in `attr` are not None.

    Will add validation messages to `errors` for every None found.

    `obj`  object to test
    `attr` string or iterable of strings to specify attributes to test
    `errors` result list to add any validation messages
    """
    for item in yield_all(attr):
        val = getattr(obj, attr)
        if val is None:
            errors.append({attr: messages.FIELD_IS_REQUIRED})


def field_must_be_none(obj, attr, errors):
    """
    Call this method from a `pylidator.validator` to check that all attributes in `attr` are None.

    Will add validation messages to `errors` for every None found.

    `obj`  object to test
    `attr` string or iterable of strings to specify attributes to test
    `errors` result list to add any validation messages
    """
    for item in yield_all(attr):
        val = getattr(obj, attr)
        if val is not None:
            errors.append({attr: messages.FIELD_MUST_BE_BLANK})


def date_is_not_after(obj, attr, errors, now, allow_none=False):
    val = getattr(obj, attr)
    if val is None:
        if not allow_none:
            errors.append({attr: messages.FIELD_IS_REQUIRED})
        return

    if val > now:
        errors.append({attr: messages.DATE_IS_NOT_AFTER})
