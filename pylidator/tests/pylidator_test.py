import unittest

import pylidator
from pylidator.exceptions import ContextNotAvailableError

from functools import wraps


def child_generator(obj):
    for row in obj.children:
        yield row


class TestObj(object):
    def __init__(self, returns):
        self.it_happened = False
        self.returns = returns
        self.children = []


@pylidator.validator(of="base_obj")
def validate_parent(obj):
    obj.it_happened = True
    return obj.returns


@pylidator.validator(of="child_obj")
def validate_child(obj_child):
    obj_child.it_happened = True
    return obj_child.returns


@pylidator.validator(of="base_obj", requires="constants_service")
def validate_parent_with_constants_service(obj_child, constants_service):
    obj_child.it_happened = True
    return obj_child.returns


class MyContext:
    pass


def _provide_base_obj(base_obj):
    yield base_obj, None


def _provide_child_obj(base_obj):
    for i, c in enumerate(base_obj.children):
        yield c, {"description": "Child {}".format(i)}


_providers = {"base_obj": _provide_base_obj, "child_obj": _provide_child_obj}


class TestPylidator(unittest.TestCase):
    def test_validator_returns_None_results_in_no_error(self):
        data = TestObj(returns=None)
        ret = pylidator.validate(data, {pylidator.ERROR: [validate_parent]}, providers=_providers)

        self.assertTrue(data.it_happened)
        self.assertEqual([], ret.get_full_results())

    def test_validator_returns_string_results_in_error(self):
        data = TestObj(returns="failed.")
        ret = pylidator.validate(data, {pylidator.ERROR: [validate_parent]}, providers=_providers)
        self.assertTrue(data.it_happened)
        self.assertEqual([{"level": "ERROR", "message": "failed.", "validation_type": None}], ret.get_full_results())

    def test_validator_returns_array_of_strings_results_in_errors(self):
        data = TestObj(returns=["error one", "error two"])
        ret = pylidator.validate(data, {pylidator.ERROR: [validate_parent]}, providers=_providers)
        self.assertEqual(
            [
                {"level": "ERROR", "message": "error one", "validation_type": None},
                {"level": "ERROR", "message": "error two", "validation_type": None},
            ],
            ret.get_full_results(),
        )

    def test_child_validator_returns_string_results_in_error_per_child(self):
        data = TestObj(returns="who cares?")

        data.children.append(TestObj(returns="hi"))
        data.children.append(TestObj(returns=["there", "you"]))
        data.children.append(TestObj(returns={"field1": ["Error 1", "Error 2"], "field2": "Error 3"}))
        data.children.append(TestObj(returns=None))

        ret = pylidator.validate(data, {pylidator.ERROR: [validate_child]}, providers=_providers)
        import pprint

        pprint.pprint(ret.get_full_results())
        self.assertEqual(
            [
                {"description": "Child 0", "level": "ERROR", "message": "hi", "validation_type": None},
                {"description": "Child 1", "level": "ERROR", "message": "there", "validation_type": None},
                {"description": "Child 1", "level": "ERROR", "message": "you", "validation_type": None},
                {
                    "description": "Child 2",
                    "field": "field1",
                    "level": "ERROR",
                    "message": "Field1: ['Error 1', 'Error 2']",
                    "validation_type": None,
                    "verbose_name": "Field1",
                },
                {
                    "description": "Child 2",
                    "field": "field2",
                    "level": "ERROR",
                    "message": "Field2: Error 3",
                    "validation_type": None,
                    "verbose_name": "Field2",
                },
            ],
            ret.get_full_results(),
        )

    def test_validator_with_constants_service_returns_string_results_in_error(self):
        data = TestObj(returns="failed.")
        cs = MyContext()
        ret = pylidator.validate(
            data,
            {pylidator.ERROR: [validate_parent_with_constants_service]},
            providers=_providers,
            extra_context={"constants_service": cs},
        )
        self.assertTrue(data.it_happened)
        self.assertEqual([{"level": "ERROR", "message": "failed.", "validation_type": None}], ret.get_full_results())

    def test_validator_requesting_unavailable_context_throws(self):
        data = TestObj(returns="failed.")
        cs = MyContext()
        with self.assertRaises(ContextNotAvailableError):
            ret = pylidator.validate(
                data,
                {pylidator.ERROR: [validate_parent_with_constants_service]},
                providers=_providers,
                extra_context={"not_constants_service": cs},
            )
