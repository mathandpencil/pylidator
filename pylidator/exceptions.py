import logging

logger = logging.getLogger(__name__)


class ContextNotAvailableError(KeyError):
    pass
