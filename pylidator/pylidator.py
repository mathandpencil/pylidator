import logging
from functools import wraps

logger = logging.getLogger(__name__)


class ContextNotAvailableError(KeyError):
    pass


class Error(dict):
    ERROR = 'ERROR'
    WARN = 'WARN'
    WARNING = 'WARN'


class ErrorLedger(object):
    ERROR = 'ERROR'
    WARN = 'WARN'
    WARNING = 'WARN'

    def __init__(self, default_object_data=None):
        self._errors = []
        self._is_valid = True
        self._default_object_data = default_object_data if default_object_data is not None else {}

    @staticmethod
    def create_error_object(message, level, object_data=None):
        if isinstance(message, dict):
            assert len(message) == 1, "Don't currently support multi key dicts inside lists."

            for field_name, error in message.items():
                error = u'{}: {}'.format(field_name, error)
                new_item = Error({'message': error, 'field': field_name})
                break

        elif isinstance(message, basestring):
            new_item = Error({'message': message})
        else:
            raise ValueError(u"Message is required and must be a string or a dict: {}".format(message))

        new_item['level'] = level
        if object_data:
            new_item.update(object_data)

        return new_item

    def add_message(self, message, level, object_data=None):
        new_item = self.create_error_object(message, level, object_data)
        new_item.update(self._default_object_data)
        self.add_object(new_item)

    def add_object(self, new_item_data):
        new_item = Error()
        new_item.update(self._default_object_data)
        new_item.update(new_item_data)

        new_item['level']
        new_item['message']

        logger.debug(u'{} {}'.format(new_item['level'], new_item['message']))

        self._errors.append(new_item)
        if new_item['level'] == self.ERROR:
            self._is_valid = False

    def get_full_results(self):
        return self._errors

    def get_error_messages(self):
        return list(unique_everseen([e['message'] for e in self._errors if e['level'] == e.ERROR]))

    def get_descriptive_error_messages(self):
        return list([u"{} {}".format(e['description'], e['message']) for e in self._errors if e['level'] == e.ERROR])

    def get_warning_messages(self):
        return list(unique_everseen([e['message'] for e in self._errors if e['level'] == e.WARN]))

    def get_errors(self):
        return [e for e in self._errors if e['level'] == e.ERROR]

    def get_warnings(self):
        return [e for e in self._errors if e['level'] == e.WARN]

    def is_valid(self):
        return self._is_valid


def validate(obj, error_validators=None, warning_validators=None, providers=None, extra_context=None,
            field_name_mapper=None, validation_type=None):
    ledger = ErrorLedger(default_object_data={'validation_type': validation_type})

    def _process_validator_results(ret, level, object_data, obj):
        # logger.debug(u'Validating {}.'.format(ret))
        if not ret:
            is_valid = True
            return is_valid

        if isinstance(ret, basestring):
            ledger.add_message(ret, level, object_data)
            is_valid = False
        elif isinstance(ret, dict):
            # The first object in the tuple is the one being validated
            if isinstance(obj, tuple):
                obj = obj[0]

            for field_name, error in ret.items():
                # verbose_field_name = ledger.map_field_name_to_verbose_name(obj, field_name)
                object_data_with_field = object_data.copy()
                object_data_with_field['field'] = field_name
                verbose_name = field_name_mapper(obj, field_name)
                if verbose_name is None:
                    from titlecase import titlecase
                    verbose_name = titlecase(' '.join(field_name.split('_')))

                object_data_with_field['verbose_name'] = verbose_name
                error = u'{}: {}'.format(verbose_name, error)
                ledger.add_message(error, level, object_data_with_field)
                is_valid = False
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
    if error_validators:
        for v in unique_everseen(error_validators):
            is_valid = v(level=ledger.ERROR, **validator_func_kwargs)
            validators_applied.append(u"{} {}".format(v.__name__, 'OK' if is_valid else 'ERROR'))

    if warning_validators:
        for v in unique_everseen(warning_validators):
            is_valid = v(level=ledger.WARN, **validator_func_kwargs)
            validators_applied.append(u"{} {}".format(v.__name__, 'OK' if is_valid else 'WARN'))

    logger.debug(u"validate complete ({} err, {} warn): {}".format(
        len(ledger.get_errors()), len(ledger.get_warnings()), ", ".join(validators_applied)))
    return ledger #{'is_valid': ledger.is_valid(), 'errors': ledger.get_errors()}


def validator(of, requires=None, affects=None):
    """
    Decorator for marking validator functions.

    `of` specifies what provider the validator should use.   The `validate` call needs an item in `providers`
         that matches `of`.
    `requires` can add additional context items, such as constants service.
    `affects` is passed through to results, as additional guidance for resolving errors.
    """

    def decorator(validator_func):
        validator_func_name = validator_func.__name__

        @wraps(validator_func)
        def actually_run_validator_func(obj, process_validator_results, providers, extra_context, level):
            kwargs = {}
            if requires:
                if isinstance(requires, basestring):
                    requires_list = requires.split()
                else:
                    requires_list = requires
                for extra_context_item in requires_list:
                    try:
                        kwargs[extra_context_item] = extra_context[extra_context_item]
                    except KeyError:
                        raise ContextNotAvailableError(
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


FIELD_IS_REQUIRED = "Field is required."


def attr_must_be_set(obj, attr, errors):
    def impl(obj, attr, errors):
        val = getattr(obj, attr)
        if val is None:
            errors.append({attr: FIELD_IS_REQUIRED})

    if isinstance(attr, basestring):
        impl(obj, attr, errors)
    else:
        for item in attr:
            impl(obj, item, errors)


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
    from itertools import ifilterfalse

    seen = set()
    seen_add = seen.add
    if key is None:
        for element in ifilterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element
