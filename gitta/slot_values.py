import pprint
from collections import defaultdict
from functools import reduce
from typing import (
    List,
    Set,
    Dict,
    Collection,
    KeysView,
    ValuesView,
    Union,
    Iterable,
    Tuple,
)

from sortedcontainers import SortedSet

from gitta.hashabledict import hashabledict
from gitta.template_elements import TemplateSlot, SlotAssignment, TemplateElement
from gitta.template import Template

empty_string_template = Template([])


def has_similar_content(
    values_set_1: Set["Template"],
    values_set_2: Set["Template"],
    relative_similarity_threshold,
):

    if relative_similarity_threshold == 1:
        return values_set_1 == values_set_2

    # If both values sets contain the empty string, don't count in overlap!
    (both_contain_empty, any_contain_empty,) = calculate_empty_string_presence(
        values_set_1, values_set_2
    )

    # Check if the intersection is larger
    intersection = values_set_1.intersection(values_set_2)
    intersection_size = len(intersection) - (1 if both_contain_empty else 0)
    union = values_set_1.union(values_set_2)
    union_size = len(union) - (1 if any_contain_empty else 0)

    return intersection_size / union_size >= relative_similarity_threshold

    # return (intersection_size / val_1_size >= relative_similarity_threshold) or (
    #     intersection_size / val_2_size >= relative_similarity_threshold
    # )


def calculate_empty_string_presence(
    values_set_1: Set["Template"], values_set_2: Set["Template"]
) -> (bool, bool):
    """ Calculates whether set_1 and/or set_2 contains empty string, as (both_contains, any_contains) tuple """
    set_1_empty_string = empty_string_template in values_set_1
    set_2_empty_string = empty_string_template in values_set_2
    both_contains = set_1_empty_string and set_2_empty_string
    any_contains = set_1_empty_string or set_2_empty_string
    return both_contains, any_contains


def _get_all_slots(templates: Collection["Template"]) -> Set[TemplateSlot]:
    return {slot for template in templates for slot in template.get_slots()}


def get_all_pure_slot_templates(templates: Collection["Template"]) -> Set["Template"]:
    """ Gets all templates that just contain a single slot as content"""
    return {
        t for t in templates if len(t.get_slots()) == 1 and len(t.get_elements()) == 1
    }


def _contains_slot_as_template(
    vals: Collection["Template"], slot: TemplateSlot
) -> bool:
    """
    Checks if the template elements contain the given slot as a single template element
    """
    slot_as_template = Template((slot,))
    return slot_as_template in vals


def get_slotless_templates(vals: Collection["Template"]) -> Set["Template"]:
    return {val for val in vals if len(val.get_slots()) == 0}


def get_indices(input_number: int, sizes: List[int]):
    current = input_number
    indices = []
    for i in range(len(sizes)):
        index = current % sizes[i]
        current = current // sizes[i]
        indices.append(index)

    return indices


def _absorb_slot_if_similar(
    i_key: TemplateSlot,
    i_vals: Set["Template"],
    j_key: TemplateSlot,
    j_vals: Set["Template"],
    new_slot_values: "SlotValues",
    relative_similarity_threshold: float,
):
    """
    j will be replaced by i if i_vals and j_vals have similar content
    """
    changed = False

    # If this slot is not already being replaced: check if it should be replaced
    if not new_slot_values.has_replacement(j_key):

        assert len(i_vals) > 0, "i_vals of a slot are of size zero! " + str(
            new_slot_values
        )
        assert len(j_vals) > 0, "j_vals of a slot are of size zero! " + str(
            new_slot_values
        )

        # Check if they have the same content
        if has_similar_content(i_vals, j_vals, relative_similarity_threshold):
            # If so, add to replacements, and replace its values
            new_slot_values.add_replacement(j_key, i_key)
            i_vals.update(j_vals)
            changed = True

    # Check if i should be replaced by j
    if not new_slot_values.has_replacement(i_key):
        if len(i_vals) == 1 and next(iter(i_vals)).get_elements() == (j_key,):
            new_slot_values.add_replacement(i_key, j_key)
            changed = True

    return changed, i_vals


def _remove_unnecessary_slot_references(changed, i_vals, new_slot_values):
    """
    Check if some slots it refers to are contained by the content of all other slots
    """
    i_vals_strings = {val for val in i_vals if not val.has_slots()}
    i_vals_slot_templates = list(get_all_pure_slot_templates(i_vals))
    i_vals_slot_templates_slots = [t.get_slots()[0] for t in i_vals_slot_templates]
    already_merged_away_idx = set()
    for idx in range(len(i_vals_slot_templates)):
        # Separate this slot and all other slots
        slot = i_vals_slot_templates_slots[idx]
        other_slots = [
            i_vals_slot_templates_slots[s_idx]
            for s_idx in range(len(i_vals_slot_templates_slots))
            if s_idx != idx and s_idx not in already_merged_away_idx
        ]

        # Calculate content of other slots + string values of element itself
        other_slots_content = {
            val for slot in other_slots for val in new_slot_values[slot]
        }.union(i_vals_strings)

        # Check if the other content already covers the content of this slot
        if other_slots_content.issuperset(new_slot_values[slot]):
            i_vals = [val for val in i_vals if val != i_vals_slot_templates[idx]]
            already_merged_away_idx.add(idx)
            changed = True
    return changed, i_vals


def _update_to_most_specific_replacement(i_key, new_slot_values):
    changed = False

    replace_key = new_slot_values.get_replacement(i_key)
    while replace_key in new_slot_values.get_replacements().keys():
        changed = True
        replace_key = new_slot_values.get_replacement(replace_key)
    new_slot_values.add_replacement(i_key, replace_key)
    return changed


def _filter_out_self(changed, i_key, i_vals):
    """
    Filters out the i_key from the i_vals if it occurs on its own, to prevent recursion to itself
    """
    if any(
        val
        for val in i_vals
        if len(val.get_elements()) == 1 and val.get_elements()[0] == i_key
    ):
        i_vals = {
            val
            for val in i_vals
            if len(val.get_elements()) != 1 or val.get_elements()[0] != i_key
        }
        changed = True
    return changed, i_vals


def _get_slot_templates(i_vals: Iterable[Template]) -> List[Template]:
    return [
        val
        for val in i_vals
        if len(val.get_elements()) == 1 and val.get_elements()[0].is_slot()
    ]


def _create_slot_index(slot_values):
    slot_indices: Dict[TemplateSlot, int] = dict()
    i = 0
    for slot in slot_values:
        slot_indices[slot] = i
        i += 1
    return slot_indices


def _remove_values_if_containg_slot_already_maps(
    changed, i, i_vals, slot_indices, slot_values
):
    for slot_template in _get_slot_templates(i_vals):
        j_key = slot_template.get_elements()[0]
        j_vals = slot_values[j_key]

        if slot_indices[j_key] > i:
            # Check if there is overlap between slot contents and this, and if so, remove it from i_values
            intersection = i_vals.intersection(j_vals)
            if len(intersection) > 0:
                i_vals = i_vals.difference(intersection)
                changed = True
    return changed, i_vals


def _replace_all_replacable_slots(changed, i_vals, slot_values):
    i_vals_slots = _get_all_slots(i_vals)
    if any(i_vals_slots.intersection(slot_values.get_replacements().keys())):
        i_vals = [t.name_template_slots(slot_values.get_replacements()) for t in i_vals]
        changed = True
    return changed, i_vals


def _merge_slot_iteration(
    slot_values: "SlotValues",
    previously_updated: Iterable[TemplateSlot],
    slot_list: List[TemplateSlot],
    slot_indices: Dict[TemplateSlot, int],
    relative_similarity_threshold: float,
):
    updated = SortedSet()
    length = len(slot_values.keys())

    # Go over all previously updated slots
    for i_slot in previously_updated:
        i = slot_indices[i_slot]
        i_changed = False

        # If this slot is not already getting replaced
        if i_slot not in slot_values.get_replacements().keys():
            i_vals = set(slot_values[i_slot])

            # Check for all other slots that are ordinally later
            for j in range(i + 1, length):
                j_key = slot_list[j]
                j_vals = slot_values[j_key]

                ij_changed, i_vals = _absorb_slot_if_similar(
                    i_slot,
                    i_vals,
                    j_key,
                    j_vals,
                    slot_values,
                    relative_similarity_threshold,
                )

                if ij_changed and j_key not in updated:
                    updated.add(j_key)

                i_changed = i_changed or ij_changed

            # Check if i values contain the j slot on itself (thus being a superset of j)
            i_changed, i_vals = _remove_values_if_containg_slot_already_maps(
                i_changed, i, i_vals, slot_indices, slot_values
            )

            # Check if some slots it refers to are contained by the content of all other slots
            i_changed, i_vals = _remove_unnecessary_slot_references(
                i_changed, i_vals, slot_values
            )

            # Check if i has replacable slots: rename these template slots to the new ones
            i_changed, i_vals = _replace_all_replacable_slots(
                i_changed, i_vals, slot_values
            )

            # Check if i contains itself
            i_changed, i_vals = _filter_out_self(i_changed, i_slot, i_vals)

            # Check if i only contains a single value
            if len(i_vals) == 1:
                single = next(iter(i_vals))
                # Check if the value it maps to is a pure slot, and if so, mark as replaced
                if (
                    len(single.get_elements()) == 1
                    and single.get_elements()[0].is_slot()
                ):
                    slot_values.add_replacement(i_slot, single.get_elements()[0])
                    i_changed = True
                # Otherwise, just replace all occurrences of this slot with the new values
                else:
                    # The slot only maps to a single piece of content.
                    # Ideally, it would be removed, but this case does not occur naturally
                    pass  # TODO: add slot removal

            # Store all newly found i_vals
            slot_values[i_slot] = i_vals

        # Replacement exists
        else:
            # Update replacement to purest replacement
            i_changed = i_changed or _update_to_most_specific_replacement(
                i_slot, slot_values
            )
        if i_changed and i_slot not in updated:
            updated.add(i_slot)

    return updated


def _remove_single_element_slot_templates(slot_values):
    """ Removes slots that only occurs once, and in a template only containing this slot.
     Example: D -> <E> | "hello" and E -> "hi" | "bonjour" becomes D -> "hello" | "hi" | "bonjour" and marking E as replaced
     """
    single_slot_occurrences: Dict[TemplateSlot, Set[TemplateSlot]] = defaultdict(
        lambda: set()
    )
    for i, i_slot in enumerate(slot_values.get_unreplaced_slots()):
        i_single_slot_values = {
            template.get_elements()[0]
            for template in slot_values[i_slot]
            if template.get_number_of_elements() == 1
            and template.get_elements()[0].is_slot()
        }

        # Register that this slot occurs as a single-element-slot-template for slot i
        for single_slot in i_single_slot_values:
            single_slot_occurrences[single_slot].add(i_slot)

    # Now check which ones occur only once, and replace them
    for redundant_slot, slots_mapping_to_slot in single_slot_occurrences.items():
        if len(slots_mapping_to_slot) == 1:
            redudant_slot_as_template = Template([redundant_slot])
            redudant_slot_values = slot_values[redundant_slot]

            containing_slot = next(iter(slots_mapping_to_slot))

            i_vals = slot_values[containing_slot]
            new_i_vals = {
                val for val in i_vals if val != redudant_slot_as_template
            }.union(redudant_slot_values)
            slot_values[containing_slot] = new_i_vals

            # Mark as updated & replaced
            # updated.add(containing_slot)
            slot_values.add_replacement(redundant_slot, containing_slot)


class SlotValues(hashabledict):
    """ Represents possible values a slot can have, assuming independence between slots  """

    def __init__(
        self,
        values: Dict[TemplateSlot, Collection["Template"]] = None,
        replacements: Dict[TemplateSlot, TemplateSlot] = None,
    ):
        if values is None:
            values = dict()
        self._replacements = (
            hashabledict(replacements) if replacements is not None else hashabledict()
        )
        super(SlotValues, self).__init__(values)

    # CONSTRUCTION
    @staticmethod
    def from_slot_assignments(assignments: Collection[SlotAssignment]):
        named_slots = list({item for key in assignments for item in key})
        named_slots.sort()

        possible_values = dict()
        for named_slot in named_slots:
            res = set()
            for content in assignments:
                if named_slot in content:
                    res.add(content[named_slot])
            possible_values[named_slot] = res

        return SlotValues(possible_values)

    def add_all_slot_values(
        self, slot_values: Union["SlotValues", Dict[TemplateSlot, Set[Template]]]
    ) -> None:
        for slot in slot_values:
            if slot in self:
                self[slot].update(slot_values[slot])
            else:
                self[slot] = set(slot_values[slot])

    # REPLACEMENTS
    def add_replacement(self, slot_from: TemplateSlot, slot_to: TemplateElement):
        self._replacements[slot_from] = slot_to
        self[slot_from] = {Template([slot_to])}

    def get_replacements(self) -> Dict[TemplateSlot, TemplateSlot]:
        return self._replacements

    def has_replacement(self, slot: TemplateSlot) -> bool:
        return slot in self._replacements

    def get_replacement(self, slot: TemplateSlot) -> TemplateSlot:
        return self._replacements[slot]

    def get_non_replaced_mappings(self) -> "SlotValues":
        result = SlotValues()
        for s in self.keys():
            if not self.has_replacement(s):
                result[s] = self[s]
        return result

    # GENERATING
    def get_all_possible_tuples(
        self, slots: Collection[TemplateSlot] = None
    ) -> Collection[Tuple[Template, ...]]:
        if slots is None:
            slots = list(self.keys())

        if len(slots) == 0:
            return SlotAssignment()

        lists = [list(self[s]) for s in slots]
        sizes = [len(l) for l in lists]
        total_possibilities = reduce(lambda x, y: x * y, sizes)

        slot_assignments = []
        for i in range(total_possibilities):
            indices = get_indices(i, sizes)
            slot_assignment = []
            for j in range(len(slots)):
                value = lists[j][indices[j]]
                slot_assignment.append(value)

            slot_assignments.append(tuple(slot_assignment))
        return slot_assignments

    def get_all_possible_assignments(
        self, slots: Collection[TemplateSlot] = None
    ) -> Collection[SlotAssignment]:
        if slots is None:
            slots = list(self.keys())
        tuples = self.get_all_possible_tuples(slots)
        result = []
        for tup in tuples:
            slot_assignment = dict()
            for j in range(len(slots)):
                slot = slots[j]
                assert slot not in slot_assignment, (
                    "Multiple slots are occuring, please use get_all_possible_tuples instead:"
                    + str(slot)
                    + " in "
                    + str(slots)
                )
                slot_assignment[slot] = tup[j]
            result.append(SlotAssignment(slot_assignment))
        return result

    # MERGING

    def merge_slots(self, relative_similarity_threshold: float = 1.0,) -> "SlotValues":
        new_slot_values = SlotValues(self)
        slot_indices = _create_slot_index(self)
        slot_list = list(self.keys())
        updated = SortedSet(self.keys())

        while len(updated) > 0:
            updated = _merge_slot_iteration(
                new_slot_values,
                updated,
                slot_list,
                slot_indices,
                relative_similarity_threshold,
            )

        # Check if there are single-element-slot-templates that occur only once
        _remove_single_element_slot_templates(new_slot_values)

        return new_slot_values

    # GETTERS
    def get_unreplaced_slots(self) -> List[TemplateSlot]:
        return [slot for slot in self.keys() if not self.has_replacement(slot)]

    # TYPED DICT OVERRIDES

    # def __eq__(self, other):
    #     if not isinstance(other, SlotValues):
    #         return False
    #     if not self.keys() == other.keys():
    #         return False
    #     for key in self.keys():
    #         if self[key] != other[key]:
    #             return False
    #     return True

    def __str__(self):
        return pprint.pformat(self)

    def keys(self) -> KeysView[TemplateSlot]:
        return super(SlotValues, self).keys()

    def values(self) -> ValuesView[Set["Template"]]:
        return super(SlotValues, self).values()

    def __setitem__(self, key: TemplateSlot, value: Set["Template"]):
        super(SlotValues, self).__setitem__(key, value)

    def __getitem__(self, key: TemplateSlot) -> Set["Template"]:
        return super(SlotValues, self).__getitem__(key)
