# pylidator
pylidator is a validation framework for Python projects.

Many business systems have complex validation rules.  This library provides a method of organizing those rules for
convenience and testability.  A `validator` method is written for each rule (or group of rules), which simply returns a
list of errors if any are found.

## Validators

A validator method checks the validity of one or a closely-related group of
assertions about a piece of data.  They all look basically like this:

```python
import pylidator

@pylidator.validator(of="child")
def child_is_valid(child):
    messages = []

    if child['age'] >= 18:
        messages.append({"age": "Child is too old."}

    if child['type'] != 'human':
        messages.append({"type": "Only humans allowed."}

    return messages
```

(Alternately, you can return just a dict of `{field: message}` items.)

## Validating Something

Once you have authored some `@pylidator.validator` methods as above, you can use them!  Try this:

```python
import pylidator

objs = {
    'name': "Mrs. Teacher's Class",
    'children': [
        {'name': "Joe", 'age': 15, 'type': 'human'},
        {'name': "Sarah", 'age': 19, 'type': 'human'},
    ]
}

# Define a provider
def _provide_child(obj):
    for i, c in enumerate(obj['children']):
        yield c, {"description": "Child {}".format(i)}

providers = {"child": _provide_something}  # "child" matches the `of` argument of the `@pylidator.validator`.
ret = pylidator.validate(objs, {pylidator.ERROR: [some_values_are_valid]}, providers=providers)
```

`child_is_valid` will be invoked once per child, and any that return something truthy will show as an ERROR.

## Function Reference

`@pylidator.validator` decorates any method that will be passed to `pylidator.validate`, and takes several optional parameters:

```
@pylidator.validator(of, requires=None, affects=None)

`of` specifies what provider the validator should use.   The `validate` call needs an item in `providers`
     that matches `of`.
`requires` (optional) can add additional context items, such as the current time or other services that can supply
     data or settings to the validator.  The requirement is fulfilled by passing `extra_context` to the `validate`
     call, containing any items that are used in a `requires`.
`affects` (optional) is simply passed through to results.  It can be used as guidance for UI/error reporting for
     helping to resolve any resultant errors.
```

```
pylidator.validate(
    obj, validators=None, providers=None, extra_context=None, field_name_mapper=None, 
    validation_type=None)

`obj` is the top-level object requiring validation.
`validators` is a dict of {level: list of `@pylidator.validator` objects}
`providers` is a dict of {of: func that takes obj and returns an iterable of some subobjects}
`extra_context` is a dict of other data that can be injected into `@pylidator.validator` with `requires`.
`field_name_mapper` is a string->string func that converts field names given in returned errors into verbose names.
`validation_type` is added as documentation into the error object.
`logging` If set to False, disables logging of validation results.
`why` String added to logging to identify the logpoint.
```
