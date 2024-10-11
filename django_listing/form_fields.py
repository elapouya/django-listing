from django import forms
from django.core import validators


class ListOfValuesField(forms.CharField):
    widget = forms.Textarea

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validators.MaxLengthValidator(1_000_000))

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return value
        return [line.strip() for line in value.split("\n") if line.strip()]

    def prepare_value(self, value):
        if isinstance(value, list):
            return "\n".join(value)
        return value
