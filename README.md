# pylidator

pylidator is a validation framework for Python projects.

Many business systems have complex validation rules.  This library provides a method of organizing those rules for
convenience and testability.  A `validator` method is written for each rule (or group of rules), which simply returns a
list of errors if any are found.

## Validators

A validator method checks the validity of one or a closely-related group of
assertions about the data.  They all look basically like this::

    @pylidator.validator(of='something')
    def something_is_true(data):
        messages = []

        if desired_condition_about_field_is_untrue:
            messages.append({'affected_field': "Should be different like this."}

        if another_desired_condition_about_the_object_is_untrue:
            messages.append('I wish this changed.')

        return messages

(Alternately, you can return just a dict of {field: message} items.)

## Argument Reference

@pylidator.validator takes several optional parameters:

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