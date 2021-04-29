import logging
from functools import wraps
from six import string_types

from .error_ledger import Error, ErrorLedger
from . import exceptions

logger = logging.getLogger(__name__)


def validate(
    obj,
    validators=None,
    providers=None,
    extra_context=None,
    field_name_mapper=None,
    validation_type=None,
    logging=True,
    why="",
    include_field_name_in_message=True,
):
    """
    `obj` is the top-level object requiring validation.
    `validators` is a dict of {level: list of `@pylidator.validator` objects}
    `providers` is a dict of {of: func that takes obj and returns an iterable of some subobjects}
    `extra_context` is a dict of other data that can be injected into `@pylidator.validator` with `requires`.
    `field_name_mapper` is a string->string func that converts field names given in returned errors into verbose names.
    `validation_type` is added into the error object.
    `logging` If set to False, disables logging of validation results.
    `why` String added to logging to identify the logpoint.
    `include_field_name_in_message` If false, the field name will not be part of the formatted error message.
    """

    ledger = ErrorLedger(default_object_data={"validation_type": validation_type}, logging=logging)

    def _process_validator_results(ret, level, object_data, obj):
        """ Process the return of a user-supplied `validator`.  Accepts lists, dicts, and strings. """

        # The first object in the tuple is the one being validated
        if isinstance(obj, tuple):
            real_obj = obj[0]
        else:
            real_obj = obj

        if not ret:
            is_valid = True
            return is_valid

        if isinstance(ret, string_types):
            ledger.add_message(ret, level, object_data)
            is_valid = False

        elif isinstance(ret, dict):
            for field_name, error in list(ret.items()):
                # verbose_field_name = ledger.map_field_name_to_verbose_name(obj, field_name)
                object_data_with_field = object_data.copy()
                object_data_with_field["field"] = field_name
                if field_name_mapper is None:
                    # raise RuntimeError("A field_name_mapper was not supplied to this validator.")
                    verbose_name = None
                else:
                    verbose_name = field_name_mapper(real_obj, field_name)
                if verbose_name is None:
                    from titlecase import titlecase

                    verbose_name = titlecase(" ".join(field_name.split("_")))

                object_data_with_field["verbose_name"] = verbose_name
                if include_field_name_in_message:
                    error = "{}: {}".format(verbose_name, error)
                else:
                    error = "{}".format(error)
                ledger.add_message(error, level, object_data_with_field)
                is_valid = False

        else:
            for validator_ret_item in ret:
                if isinstance(validator_ret_item, str):
                    ledger.add_message(validator_ret_item, level, object_data)
                    is_valid = False
                elif isinstance(validator_ret_item, dict):
                    for field_name, error in list(validator_ret_item.items()):
                        # verbose_field_name = ledger.map_field_name_to_verbose_name(obj, field_name)
                        object_data_with_field = object_data.copy()
                        object_data_with_field["field"] = field_name
                        verbose_name = field_name_mapper(real_obj, field_name)
                        if verbose_name is None:
                            from titlecase import titlecase

                            verbose_name = titlecase(" ".join(field_name.split("_")))

                        object_data_with_field["verbose_name"] = verbose_name
                        if include_field_name_in_message:
                            error = "{}: {}".format(verbose_name, error)
                        else:
                            error = "{}".format(error)

                        ledger.add_message(error, level, object_data_with_field)
                        is_valid = False

        return is_valid

    # global _cached_provided_items
    _cached_provided_items = {None: [obj]}

    def get_provided_items(of):
        # global _cached_provided_items

        if of in _cached_provided_items:
            return _cached_provided_items[of]

        # Already in cache...
        # if of is None:
        #     return [obj]

        # Use the correct `provider` to find the child object to process with the validator func.
        # The provider will generate all child objects and call the validator func once per yielded object.
        try:
            generator = providers[of]
        except (KeyError, TypeError):
            raise KeyError("Must add `{}` to providers for validator `{}`.".format(of, validator_func_name))

        ret = tuple(generator(obj))
        _cached_provided_items[of] = ret
        return ret

    validator_func_kwargs = {
        "process_validator_results": _process_validator_results,
        "extra_context": extra_context,
        "get_provided_items_f": get_provided_items,
    }

    validators_applied = []
    for level, level_validators in validators.items():
        # assert level in Error.LEVELS, "Level `{}` is not recognized.".format(level)

        for v in unique_everseen(level_validators):
            is_valid = v(level=level, **validator_func_kwargs)
            validators_applied.append("{} {}".format(v.__name__, "OK" if is_valid else str(level)))

    if logging:
        if why:
            why = why.strip() + ": "
        else:
            why = ""
        if len(ledger.get_errors()) + len(ledger.get_warnings()) == 0:
            logger.debug(
                "{}validate complete ({} err, {} warn)".format(
                    why, len(ledger.get_errors()), len(ledger.get_warnings())
                )
            )
        else:
            logger.debug(
                "{}validate complete ({} err, {} warn): {}".format(
                    why, len(ledger.get_errors()), len(ledger.get_warnings()), ", ".join(validators_applied)
                )
            )

    return ledger


def validator(of, requires=None, affects=None):
    """
    Decorator for marking validator functions.

    `of` specifies what provider the validator should use.   The `validate` call needs an item in `providers`
         that matches `of`.
    `requires` (optional) can add additional context items, such as the current time or other services that can supply
         data or settings to the validator.  The requirement is fulfilled by passing `extra_context` to the `validate`
         call, containing any items that are used in a `requires`.
    `affects` (optional) is simply passed through to results.  It can be used as guidance for UI/error reporting for
         helping to resolve any resultant errors.
    """

    def decorator(validator_func):
        validator_func_name = validator_func.__name__

        @wraps(validator_func)
        def actually_run_validator_func(process_validator_results, get_provided_items_f, extra_context, level):
            """`actually_run_validator_func` gets called directly from `validate` above, once per unique validation method in
            `validators`.
            """
            kwargs = {}
            if requires:
                if isinstance(requires, string_types):
                    requires_list = requires.split()
                else:
                    requires_list = requires
                for extra_context_item in requires_list:
                    try:
                        kwargs[extra_context_item] = extra_context[extra_context_item]
                    except (KeyError, TypeError) as exc:
                        raise exceptions.ContextNotAvailableError(
                            "{} is not available in the validator context.".format(extra_context_item)
                        )

            # logger.debug(u'Validating {} of {} (of={}).'.format(validator_func, obj, of))
            is_valid = True
            for item in get_provided_items_f(of):
                try:
                    row, object_data = item
                except ValueError:
                    raise ValueError("{} must yield 2-tuples, got {}".format(generator, item))
                assert object_data is None or isinstance(
                    object_data, dict
                ), "Object data returned from provider must be None or dict of values, but got {}".format(
                    type(object_data)
                )

                if object_data is None:
                    object_data = {}

                if affects:
                    object_data["affects"] = affects

                ret = validator_func(row, **kwargs)
                row_is_valid = process_validator_results(ret, level=level, object_data=object_data, obj=row)
                if not row_is_valid:
                    is_valid = False

            return is_valid

        return actually_run_validator_func

    return decorator


def format_results(validator_results):
    if validator_results.is_valid():
        return "is valid."

    def format_result_item(err):
        err = err.copy()

        level = err.pop("level")
        message = err.pop("message")
        description = err.pop("description", "(no description)")

        therest = ", ".join("{}={}".format(x, y) for x, y in err.items())
        return "{} {} {} {}".format(level, description, message, therest)

    return "\n".join((format_result_item(err) for err in validator_results.get_full_results()))


def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    from future.moves.itertools import filterfalse

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
