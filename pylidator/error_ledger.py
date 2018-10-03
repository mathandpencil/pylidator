import logging

logger = logging.getLogger(__name__)


class Error(dict):
    ERROR = 'ERROR'
    WARN = 'WARN'
    WARNING = 'WARN'

    LEVELS = [
        ERROR,
        WARN
    ]


class ErrorLedger(object):
    ERROR = 'ERROR'
    WARN = 'WARN'
    WARNING = 'WARN'

    def __init__(self, default_object_data=None, custom_field_name_mapper=None):
        """
        `custom_field_name_mapper` is an optional callable that takes the field name and returns
            a verbose_name for the field.
        """
        self._errors = []
        self._is_valid = True
        self._default_object_data = default_object_data if default_object_data is not None else {}
        self._custom_field_name_mapper = custom_field_name_mapper

    def create_error_object(self, message, level, object_data=None):
        if isinstance(message, dict):
            assert len(message) == 1, "Don't currently support multi key dicts inside lists."

            for field_name, error in message.items():
                verbose_name = self.map_field_name_to_verbose_name(field_name)
                error = u'{}: {}'.format(verbose_name, error)
                new_item = Error({'message': error, 'field': field_name, 'verbose_name': verbose_name})
                break

        elif isinstance(message, str):
            new_item = Error({'message': message})

        else:
            raise ValueError(u"Message is required and must be a string or a dict: {}".format(message))

        new_item['level'] = level
        if object_data:
            new_item.update(object_data)

        return new_item

    def map_field_name_to_verbose_name(self, field_name):
        verbose_name = None

        if self._custom_field_name_mapper is not None:
            verbose_name = self._custom_field_name_mapper(field_name)
        if verbose_name is None:
            from titlecase import titlecase
            verbose_name = titlecase(' '.join(field_name.split('_')))
        return verbose_name

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

