from functools import total_ordering
from typing import Dict, KeysView, ValuesView

from gitta.hashabledict import hashabledict


class TemplateElement:
    def __init__(self):
        pass

    def get_content(self):
        return None

    def is_slot(self):
        return False

    def is_named(self):
        return False

    def __repr__(self):
        return self.__str__()


class TemplateString(TemplateElement):
    def __init__(self, content):
        super().__init__()
        self._content = content

    def get_content(self):
        return self._content

    def __str__(self):
        return self._content

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, TemplateString):
            return self._content == other._content
        return False

    def __hash__(self):
        return hash(self._content)


@total_ordering
class TemplateSlot(TemplateElement):
    def __init__(self):
        super().__init__()
        pass

    def is_slot(self):
        return True

    def __str__(self):
        return "[SLOT]"

    def __lt__(self, other: "NamedTemplateSlot"):
        return id(self) < id(other)

    def get_name(self):
        raise Exception("Unnamed template slots do not have a name")


@total_ordering
class NamedTemplateSlot(TemplateSlot):
    def __init__(self, name):
        super().__init__()
        self._name = name

    def is_named(self):
        return True

    def get_name(self):
        return self._name

    def __str__(self):
        return "<" + self._name + ">"

    def __lt__(self, other: "NamedTemplateSlot"):
        return self._name < other._name

    def __eq__(self, obj):
        return isinstance(obj, NamedTemplateSlot) and obj._name == self._name

    def __hash__(self):
        return hash(self._name)


class SlotAssignment(hashabledict):
    """ Representing a single mapping from template slots to a sub-template"""

    def __init__(self, values: Dict[TemplateSlot, "Template"] = None):
        if values is None:
            values = dict()
        super(SlotAssignment, self).__init__(values)

    def keys(self) -> KeysView[TemplateSlot]:
        return super(SlotAssignment, self).keys()

    def values(self) -> ValuesView["Template"]:
        return super(SlotAssignment, self).values()

    def contains_empty_string_assignment(self):
        return any(len(v.get_elements()) == 0 for v in self.values())

    def __setitem__(self, key: TemplateSlot, value: "Template"):
        super(SlotAssignment, self).__setitem__(key, value)

    def __getitem__(self, key: TemplateSlot) -> "Template":
        return super(SlotAssignment, self).__getitem__(key)
