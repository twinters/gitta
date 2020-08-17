import re
from functools import lru_cache
from typing import (
    List,
    Callable,
    Tuple,
    Set,
    Optional,
    Dict,
    Iterator,
    Iterable,
    Collection,
)

import numpy as np
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer
from typing.re import Match

from src.wagnerfischer import WagnerFischer
from src.template_elements import (
    TemplateElement,
    TemplateString,
    TemplateSlot,
    SlotAssignment,
    NamedTemplateSlot,
)


default_named_slot_regex = re.compile("<([a-zA-Z0-9_-]+)>")


class Template:
    def __init__(self, elements: Iterable[TemplateElement]):
        self._elements = tuple(elements)

    # CHECKERS
    def is_flat_string(self) -> bool:
        return len([el for el in self._elements if el.is_slot()]) == 0

    def covers_string(self, text: str) -> bool:
        return self.covers(Template.from_string(text))

    def covers(self, template: "Template") -> bool:
        return _covers(self._elements, template._elements)

    def encompasses(self, template: "Template", slot_values: "SlotValues"):
        if not self.covers(template):
            return False
        all_mappings = self.create_slot_mapping_all(template)
        for mapping in all_mappings:
            still_encompasses = True
            for slot in mapping.keys():
                mapped_slot: Template = mapping[slot]
                allowed_values_for_slot = slot_values[slot]

                # Check if the function maps to itself
                maps_to_itself = (
                    len(mapped_slot.get_elements()) == 1
                    and len(mapped_slot.get_slots()) == 1
                    and mapped_slot.get_slots()[0] == slot
                )
                if not maps_to_itself and mapped_slot not in allowed_values_for_slot:
                    still_encompasses = False
                    break

            if still_encompasses:
                return True

        return False

    def has_same_shape(self, template: "Template") -> bool:
        """
        Calculates if two templates have the same shape, i.e. same length, same TemplateTexts and slots in same place
        """
        if len(self._elements) != len(template._elements):
            return False

        for i in range(len(self._elements)):
            self_element = self._elements[i]
            other_element = template._elements[i]
            # If one is slot and other isn't, then not same shape
            if self_element.is_slot() != other_element.is_slot():
                return False
            # If they are not slots, and not equal, then also not same shape
            elif not self_element.is_slot() and self_element != other_element:
                return False
        return True

    def __eq__(self, template: "Template") -> bool:
        if not isinstance(template, Template):
            return False

        if len(self._elements) != len(template._elements):
            return False

        for i in range(len(self._elements)):
            self_element = self._elements[i]
            other_element = template._elements[i]
            if self_element.is_slot():
                if not other_element.is_slot():
                    return False
                if self_element.is_named() != other_element.is_named():
                    return False
                if (
                    self_element.is_named()
                    and other_element.is_named()
                    and self_element != other_element
                ):
                    return False
            else:
                if other_element.is_slot():
                    return False
                elif self_element.get_content() != template._elements[i].get_content():
                    return False
        return True

    def __hash__(self) -> int:
        return hash(
            tuple(element for element in self._elements if not element.is_slot())
        )

    # DATA ACCESS
    def get_number_of_elements(self):
        return len(self._elements)

    def to_flat_string(
        self,
        detokenizer: Callable[[List[str]], str] = TreebankWordDetokenizer().detokenize,
    ):
        elements = [str(el) for el in self._elements]
        return detokenizer(elements)

    def __str__(self):
        return '"' + self.to_flat_string() + '"'

    def __repr__(self):
        return self.__str__()

    def get_elements(self):
        return self._elements

    @lru_cache()
    def get_number_of_slots(self):
        return sum(1 for el in self._elements if el.is_slot())

    @lru_cache()
    def get_number_of_non_slots(self):
        return sum(1 for el in self._elements if not el.is_slot())

    def length(self):
        return len(self._elements)

    def get_slots(self) -> List[TemplateSlot]:
        return [
            el for el in self._elements if isinstance(el, TemplateSlot) and el.is_slot()
        ]

    def has_slots(self):
        return len(self.get_slots()) > 0

    def extract_content(self, other: "Template") -> Tuple["Template"]:
        """
        Finds an assignment of slots to parts of the given template,
        returned as a list of templates (which contain the relevant template elements)
        """
        all_possibilities = self.extract_content_all(other)
        if all_possibilities is not None and len(all_possibilities) > 0:
            return _select_lowest_variance_slot_assignment(all_possibilities)

    def extract_content_all(self, other: "Template") -> Set[Tuple["Template"]]:
        assert self.covers(other), (
            "Template " + str(self) + " does not cover " + str(other)
        )
        return _extract_content_from_slots(self._elements, other._elements)

    def extract_content_as_slot_assignment(self, other: "Template") -> SlotAssignment:
        extracted = self.extract_content(other)
        return self.create_slot_mapping(extracted)

    def get_slot_values(
        self, more_specific_templates: Iterable["Template"]
    ) -> Dict[TemplateSlot, Set["Template"]]:
        """
         Returns what values a slot can map to.
         Very similar to "create_slot_mapping" if there are no multiple same named slots in this template
        """
        result: Dict[TemplateSlot, Set["Template"]] = dict()
        template_slots = self.get_slots()
        for template in more_specific_templates:
            slot_values = self.create_slot_values_mapping(template)
            for s in slot_values:
                if s in result:
                    result[s].update(slot_values[s])
                else:
                    result[s] = slot_values[s]

        return result

    def create_slot_values_mapping(
        self, template: "Template"
    ) -> Dict[TemplateSlot, Set["Template"]]:
        """
        Does the same as create_slot_mapping, but can deal with multiple slots having the same name in the template, by assuming independence
        """
        template_slots = self.get_slots()
        extracted = self.extract_content(template)

        assert len(template_slots) == len(extracted)
        slot_values = dict()
        for i in range(len(template_slots)):
            slot = template_slots[i]
            content = extracted[i]
            if slot not in slot_values:
                slot_values[slot] = {content}
            else:
                slot_values[slot].add(content)
        return slot_values

    def create_slot_mapping(
        self, tup: Tuple["Template"], template_slots=None
    ) -> SlotAssignment:
        if template_slots is None:
            template_slots = self.get_slots()

        # The template slots should not have the same values
        assert len(template_slots) == len(
            set(template_slots)
        ), "Template slot has multiple slots with the same name. Use create_slot_values_mapping instead."

        assert len(template_slots) == len(tup)
        mapping = SlotAssignment()
        for i in range(len(tup)):
            mapping[template_slots[i]] = tup[i]
        return mapping

    def create_slot_mapping_all(self, other: "Template") -> Set[SlotAssignment]:
        template_slots = self.get_slots()

        all_mappings = set()

        for tup in self.extract_content_all(other):
            mapping = SlotAssignment()
            for i in range(len(tup)):
                mapping[template_slots[i]] = tup[i]
            all_mappings.add(mapping)
        return all_mappings

    # STATIC CREATORS
    def fill(self, slot_assignments: SlotAssignment) -> "Template":
        new_elements = []
        for el in self._elements:
            if el in slot_assignments:
                new_elements.extend(slot_assignments[el]._elements)
            else:
                new_elements.append(el)
        return Template(new_elements)

    def fill_with_tuple(self, content: Tuple["Template"]) -> "Template":
        new_elements = []
        index = 0
        for el in self._elements:
            if el.is_slot():
                new_elements.extend(content[index]._elements)
                index += 1
            else:
                new_elements.append(el)
        return Template(new_elements)

    def fill_with_strings(self, strings: List[str]) -> "Template":
        slot_assignments = SlotAssignment()
        slots = self.get_slots()
        if len(slots) != len(strings):
            raise Exception(
                "Can not fill in "
                + str(len(slots))
                + " slots using "
                + str(len(strings))
                + "strings: "
                + str(strings)
            )

        for i in range(len(slots)):
            slot_assignments[slots[i]] = Template.from_string(strings[i])
        return self.fill(slot_assignments)

    @staticmethod
    def from_string(
        content: str,
        named_slot_regex=default_named_slot_regex,
        tokenizer: Callable[[str], List[str]] = word_tokenize,
        slot_token: str = "[SLOT]",
    ) -> "Template":
        if slot_token in content or named_slot_regex.search(content):
            # If a variable token is defined: split on the variables and add them in between
            parts = content.split(slot_token)
            tokens = []
            for i in range(len(parts)):
                part = parts[i]

                part_parts = []
                last_match: Match = named_slot_regex.search(part)
                while last_match:

                    # Split in three parts
                    part_part_until_match = part[: last_match.start()]
                    part_match = part[last_match.start() : last_match.end()]
                    part_from_match = part[last_match.end() :]

                    # Tokenize first
                    part_tokens = tokenizer(part_part_until_match)
                    tokens += [TemplateString(t) for t in part_tokens]

                    # Make slot name out of second part
                    named_slot_name = named_slot_regex.findall(part_match)[0]
                    named_slot = NamedTemplateSlot(named_slot_name)
                    tokens += [named_slot]

                    # Further process third
                    part = part_from_match
                    if len(part.strip()) > 0:
                        last_match = named_slot_regex.search(part)
                    else:
                        last_match = None

                if len(part.strip()) > 0:
                    part_tokens = tokenizer(part)
                    tokens += [TemplateString(t) for t in part_tokens]

                # Add variable token in between
                if i < len(parts) - 1:
                    tokens += [TemplateSlot()]
        else:
            tokens = [TemplateString(t) for t in tokenizer(content)]
        return Template(tokens)

    @staticmethod
    def from_string_tokens(elements: List[str], slot_token: str = None) -> "Template":
        return Template(
            [
                TemplateSlot() if el == slot_token else TemplateString(el)
                for el in elements
            ]
        )

    @staticmethod
    def merge_templates_wagner_fischer(
        template1: "Template",
        template2: "Template",
        minimal_variables: bool = True,
        allow_longer_template=False,
        min_non_slot_elements=None,
    ) -> Iterator["Template"]:
        distances_table = WagnerFischer(template1._elements, template2._elements)

        def is_valid_merge(t: Template) -> bool:
            return allow_longer_template or (
                t.length() <= template1.length() or t.length() <= template2.length()
            )

        return (
            val
            for val in (
                Template(
                    convert_template_elements_from_wagner_fischer(
                        template1._elements,
                        alignment,
                        minimal_variables=minimal_variables,
                        merge_named_slots=True,
                    )
                )
                for alignment in distances_table.alignments()
            )
            if is_valid_merge(val)
            and (
                min_non_slot_elements is None
                or val.get_number_of_non_slots() >= min_non_slot_elements
            )
        )

    def name_template_slots(self, slot_map: Dict[TemplateSlot, TemplateSlot]):
        new_elements = [
            slot_map[e]
            if isinstance(e, TemplateSlot) and e.is_slot() and e in slot_map
            else e
            for e in self._elements
        ]
        return Template(new_elements)

    @staticmethod
    def merge_all(
        templates: List["Template"],
        minimal_variables: bool = True,
        default: "Template" = None,
    ) -> "Template":
        """
        Merges all templates into a single template that generalises all.
        Will automatically stop if it has the same shape as the given default, if one is given
        :param templates: Templates to merge
        :param default: (optional) A template that already generalises the other templates, such that it will stop
                merging once it reaches this template
        :return: A template more general than all given templates
        """
        if len(templates) == 0:
            return default
        current_template = templates[0]
        default_non_slot_elements = (
            default.get_number_of_non_slots() if default is not None else None
        )
        for i in range(1, len(templates)):
            try:
                current_template = next(
                    Template.merge_templates_wagner_fischer(
                        current_template,
                        templates[i],
                        minimal_variables=minimal_variables,
                        min_non_slot_elements=default_non_slot_elements,
                    )
                )
            except StopIteration:
                pass  # If doesn't have something as equally short as default, just continue
            if default is not None and default.has_same_shape(current_template):
                return default
        return current_template


# COVERING


def _covers(
    main_template_elements: Tuple[TemplateElement],
    test_template_elements: Tuple[TemplateElement],
) -> bool:
    # If no more main template elements: check if test template is also empty, otherwise it doesn't cover
    if len(main_template_elements) == 0:
        return len(test_template_elements) == 0

    # (main_template_elements not empty)
    # If test template elements is empty, check if the main template elements only contains slots
    if len(test_template_elements) == 0:
        return all(element.is_slot() for element in main_template_elements)

    # (both lists have more than one element
    main_first = main_template_elements[0]
    test_first = test_template_elements[0]

    # If main is slot: check with and without current test token in front
    if main_first.is_slot():
        return (
            # Slot covers no (more) elements
            _covers(main_template_elements[1:], test_template_elements)
            # Slot covers this one and also potentialy future ones
            or _covers(main_template_elements, test_template_elements[1:])
        )

    # (main_first is not a slot)
    # If test_first is a slot, and main_first not, then it can not cover
    if test_first.is_slot():
        return False

    # If both not slots, check equality for them and check if rest covers
    if not main_first.is_slot() and not test_first.is_slot():
        return main_first.get_content() == test_first.get_content() and _covers(
            main_template_elements[1:], test_template_elements[1:]
        )


# EXTRACTION


def _extract_content_from_slots(
    main_template_elements: Tuple[TemplateElement],
    test_template_elements: Tuple[TemplateElement],
) -> Optional[Set[Tuple[Template]]]:
    # If empty: only return things if the other is also empty, if so, return set, if not, return None
    if len(main_template_elements) == 0:
        if len(test_template_elements) == 0:
            empty_template_list: List[Template] = []
            return {tuple(empty_template_list)}
        else:
            return None

    # (main_templates_elements not empty)
    # If test template elements is empty, check if the main template elements only contains slots
    if len(test_template_elements) == 0:
        if all(element.is_slot() for element in main_template_elements):
            return {tuple([Template([]) for _ in main_template_elements])}

    # (both lists have more than one element
    main_first: TemplateElement = main_template_elements[0]
    test_first: TemplateElement = test_template_elements[0]

    # If main is slot: check with and without current test token in front
    if main_first.is_slot():
        possibilities = set()
        # Slot covers no (more) elements
        if _covers(main_template_elements[1:], test_template_elements):
            existing_tuples: Set[Tuple[Template]] = _extract_content_from_slots(
                main_template_elements[1:], test_template_elements
            )
            # Add a blank option to all existing tuples
            new_tuples = [
                tuple([Template.from_string("")] + list(tup)) for tup in existing_tuples
            ]
            possibilities.update(new_tuples)

        # Slot covers this one and also potentialy future ones
        if _covers(main_template_elements, test_template_elements[1:]):
            further_possibilities: Set[Tuple[Template]] = _extract_content_from_slots(
                main_template_elements, test_template_elements[1:]
            )
            extended_further_possibilities = [
                _add_prefix_to_first(test_first, tup) for tup in further_possibilities
            ]
            possibilities.update(extended_further_possibilities)
        return possibilities

    # (main_first is not a slot)
    # If test_first is a slot, and main_first not, then it can not cover
    if test_first.is_slot():
        return None

    # If both not slots, check equality for them and check if rest covers
    if not main_first.is_slot() and not test_first.is_slot():
        if main_first.get_content() == test_first.get_content():
            return _extract_content_from_slots(
                main_template_elements[1:], test_template_elements[1:]
            )
        else:
            return None


def _add_prefix_to_first(
    prefix: TemplateElement, tup: Tuple[Template]
) -> Tuple[Template]:
    if len(tup) == 0:
        return tuple([Template([prefix])])
    front_subtemplate: Template = tup[0]
    new_front_subtemplate_content = [prefix]
    new_front_subtemplate_content.extend(front_subtemplate.get_elements())

    new_first_element = Template(new_front_subtemplate_content)
    new_tuple = [new_first_element] + list(tup)[1:]
    return tuple(new_tuple)


def _select_lowest_variance_slot_assignment(
    possibilities: Set[Tuple[Template]],
) -> Tuple[Template]:
    options_list = list(possibilities)
    if len(options_list) == 1:
        return options_list[0]

    variances = [
        np.var([len(assignment.get_elements()) for assignment in option])
        for option in options_list
    ]
    lowest_var_index = int(np.argmin(variances))
    return options_list[lowest_var_index]


# CONVERTING


def _has_ending_slot(
    elements: List[TemplateElement],
        merge_named_slots: bool = False
) -> bool:
    return (
        len(elements) > 0
        and elements[len(elements) - 1].is_slot()
        and (not elements[len(elements) - 1].is_named() or merge_named_slots)
    )


def convert_template_elements_from_wagner_fischer(
    elements: Tuple[TemplateElement],
    alignment: List[str],
    minimal_variables=True,
    merge_named_slots=False,
) -> List[TemplateElement]:
    resulting_elements = []
    elements_index = 0

    for operation in alignment:
        if operation == "M":  # KEEP
            new_element: TemplateElement = elements[elements_index]
            if not new_element.is_slot() or (
                not minimal_variables
                or not _has_ending_slot(resulting_elements, merge_named_slots)
            ):
                # Remove last slot if it is named and there is a new slot coming in
                if (
                    new_element.is_slot()
                    and len(elements) > 1
                    and merge_named_slots
                    and elements[len(elements) - 1].is_named()
                ):
                    resulting_elements.pop()
                resulting_elements.append(new_element)
            elements_index += 1
        elif operation == "S":  # SUBSTITUTE -> add slot
            if not minimal_variables or not _has_ending_slot(
                resulting_elements, False
            ):
                resulting_elements.append(TemplateSlot())
            elements_index += 1
        elif operation == "D":  # DELETE -> skip element
            if not _has_ending_slot(resulting_elements, False):
                resulting_elements.append(TemplateSlot())
            elements_index += 1
        elif operation == "I":  # INSERT -> add slot & stay
            if not _has_ending_slot(resulting_elements, False):
                resulting_elements.append(TemplateSlot())

    return resulting_elements
