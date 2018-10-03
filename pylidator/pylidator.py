import logging
from functools import wraps

from .error_ledger import Error, ErrorLedger
from . import exceptions

logger = logging.getLogger(__name__)


def validate(obj, validators=None, providers=None, extra_context=None,
            field_name_mapper=None, validation_type=None):

    ledger = ErrorLedger(
        default_object_data={'validation_type': validation_type},
        custom_field_name_mapper=field_name_mapper)

    def _process_validator_results(ret, level, object_data, obj):
        """ Process the return of a user-supllied `validator`.  Accepts lists, dicts, and strings. """

        # The first object in the tuple is the one being validated
        if isinstance(obj, tuple):
            real_obj = obj[0]
        else:
            real_obj = obj

        if not ret:
            is_valid = True
            return is_valid

        if isinstance(ret, str):
            ledger.add_message(ret, level, object_data)
            is_valid = False

        elif isinstance(ret, dict):
            ledger.add_message(ret, level, object_data)
            if len(ret) > 0: is_valid = False

        else:
            for error in ret:
                ledger.add_message(error, level, object_data)
                is_valid = False

        return is_valid

    validator_func_kwargs = {
        'obj': obj,
        'process_validator_results': _process_validator_results,
        'providers': providers,
        'extra_context': extra_context,
    }

    validators_applied = []
    for level, level_validators in validators.items():
        assert level in Error.LEVELS, u"Level `{}` is not recognized.".format(level)

        for v in unique_everseen(level_validators):
            is_valid = v(level=level, **validator_func_kwargs)
            validators_applied.append(u"{} {}".format(v.__name__, 'OK' if is_valid else str(level)))

    logger.debug(u"validate complete ({} err, {} warn): {}".format(
        len(ledger.get_errors()), len(ledger.get_warnings()), ", ".join(validators_applied)))
    return ledger #{'is_valid': ledger.is_valid(), 'errors': ledger.get_errors()}


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
        def actually_run_validator_func(obj, process_validator_results, providers, extra_context, level):
            kwargs = {}
            if requires:
                if isinstance(requires, str):
                    requires_list = requires.split()
                else:
                    requires_list = requires
                for extra_context_item in requires_list:
                    try:
                        kwargs[extra_context_item] = extra_context[extra_context_item]
                    except KeyError:
                        raise exceptions.ContextNotAvailableError(
                            u"{} is not available in the validator context.".format(extra_context_item))

            # logger.debug(u'Validating {} of {} (of={}).'.format(validator_func, obj, of))
            is_valid = True
            if of is None:
                # If `of` None, no provider needed.  Just call the validator func directly with the object from `validate`.
                ret = validator_func(obj, **kwargs)
                object_data = {}
                if affects:
                    object_data['affects'] = affects
                is_valid = process_validator_results(ret, level=level, object_data=object_data, obj=obj)
            else:
                # Use the correct `provider` to find the child object to process with the validator func.
                # The provider will generate all child objects and call the validator func once per yielded object.
                try:
                    generator = providers[of]
                except (KeyError, TypeError):
                    raise KeyError(u"Must add `{}` to providers for validator `{}`.".format(of, validator_func_name))

                for row, object_data in generator(obj):
                    assert object_data is None or isinstance(object_data, dict), \
                        u"Object data returned from provider must be None or dict of values, but got {}".format(
                            type(object_data))

                    if affects:
                        if object_data is None:
                            object_data = {}
                        object_data['affects'] = affects

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

        level = err.pop('level')
        message = err.pop('message')
        description = err.pop('description', '(no description)')

        therest = u', '.join(u'{}={}'.format(x,y) for x,y in err.items())
        return u'{} {} {} {}'.format(level, description, message, therest)

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
