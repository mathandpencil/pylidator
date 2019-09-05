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


class Tests(unittest.TestCase):
    def test_field_name_mapper_with_children_changes_field_name(self):
        def _custom_field_name_mapper(obj, field_name):
            return field_name + "_mapped"

        data = TestObj(returns={"field1": ["Error 1", "Error 2"], "field2": "Error 3"})

        data.children.append(TestObj(returns={"field1": "Broken"}))
        data.children.append(TestObj(returns={"field1": ["Error 1", "Error 2"], "field2": "Error 3"}))
        data.children.append(TestObj(returns=None))

        ret = pylidator.validate(
            data,
            {pylidator.ERROR: [validate_parent, validate_child]},
            providers=_providers,
            field_name_mapper=_custom_field_name_mapper,
        )

        self.assertEqual(
            [
                {
                    "field": "field1",
                    "level": "ERROR",
                    "message": "field1_mapped: ['Error 1', 'Error 2']",
                    "validation_type": None,
                    "verbose_name": "field1_mapped",
                },
                {
                    "field": "field2",
                    "level": "ERROR",
                    "message": "field2_mapped: Error 3",
                    "validation_type": None,
                    "verbose_name": "field2_mapped",
                },
                {
                    "description": "Child 0",
                    "field": "field1",
                    "level": "ERROR",
                    "message": "field1_mapped: Broken",
                    "validation_type": None,
                    "verbose_name": "field1_mapped",
                },
                {
                    "description": "Child 1",
                    "field": "field1",
                    "level": "ERROR",
                    "message": "field1_mapped: ['Error 1', 'Error 2']",
                    "validation_type": None,
                    "verbose_name": "field1_mapped",
                },
                {
                    "description": "Child 1",
                    "field": "field2",
                    "level": "ERROR",
                    "message": "field2_mapped: Error 3",
                    "validation_type": None,
                    "verbose_name": "field2_mapped",
                },
            ],
            ret.get_full_results(),
        )

