import json
import math
import random
import re
from functools import reduce
from queue import Queue
from typing import Dict, Collection, Callable, List, Optional, Set, Iterator, Tuple

from gitta.hashabledict import hashabledict
from gitta.template import Template, default_named_slot_regex
from gitta.slot_values import SlotValues
from gitta.template_elements import TemplateSlot, NamedTemplateSlot, SlotAssignment
from gitta.template_tree import TemplateTree

default_depth = 100


class SlotReplacements:
    def __init__(self, replacements: Dict[TemplateSlot, TemplateSlot] = None):
        if replacements is None:
            replacements = hashabledict()
        self._replacements = hashabledict(replacements)

    def merge(self, slot_replacements: "SlotReplacements") -> "SlotReplacements":
        if not self.is_compatible_with_slot_replacements(slot_replacements):
            raise Exception()

        merged = dict(self._replacements)
        for key in slot_replacements._replacements:
            merged[key] = slot_replacements._replacements[key]

        return SlotReplacements(merged)

    def merge_all(
        self, possible_new_slot_replacements: Collection["SlotReplacements"]
    ) -> Collection["SlotReplacements"]:
        return {self.merge(repl) for repl in possible_new_slot_replacements}

    def add(self, template_slot: TemplateSlot, replacement_slot: TemplateSlot):
        if self.has_replacement(template_slot):
            if self.get_replacement(template_slot) == replacement_slot:
                return self
            else:
                raise Exception("Already existing", template_slot)

        new_replacements = dict(self._replacements)
        new_replacements[template_slot] = replacement_slot
        return SlotReplacements(new_replacements)

    def get_replacement(self, template_slot: TemplateSlot) -> TemplateSlot:
        return self._replacements[template_slot]

    def has_replacement(self, template_slot: TemplateSlot) -> bool:
        return template_slot in self._replacements

    def is_compatible_with(
        self, template_slot: TemplateSlot, replacement_slot: TemplateSlot
    ) -> bool:
        return (
            not self.has_replacement(template_slot)
            or self.get_replacement(template_slot) == replacement_slot
        )

    def is_compatible_with_slot_replacements(
        self, slot_replacements: "SlotReplacements"
    ):
        return all(
            self.is_compatible_with(repl, slot_replacements.get_replacement(repl))
            for repl in slot_replacements._get_replacements()
        )

    def _get_replacements(self) -> Dict[TemplateSlot, TemplateSlot]:
        return self._replacements

    def __str__(self):
        return str(self._replacements)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self._replacements)

    def __eq__(self, other: "SlotReplacements"):
        if not isinstance(other, SlotReplacements):
            return False
        return self._replacements == other._replacements


class ContextFreeGrammar:
    def __init__(
        self,
        grammar: Dict[TemplateSlot, Collection[Template]],
        start=NamedTemplateSlot("origin"),
    ):
        self._grammar: Dict[TemplateSlot, Collection[Template]] = hashabledict(grammar)
        self._start = start

    @staticmethod
    def from_string(
        grammar: Dict[str, Collection[str]],
        template_parser: Callable[[str], Template] = Template.from_string,
    ) -> "ContextFreeGrammar":

        input_dict = dict()

        for key in grammar.keys():
            slot_key = NamedTemplateSlot(key)
            string_values = grammar[key]

            # If only one string is given, cast as list
            if isinstance(string_values, str):
                string_values = [string_values]

            template_values = [template_parser(val) for val in string_values]

            input_dict[slot_key] = template_values

        return ContextFreeGrammar(input_dict)

    @staticmethod
    def from_template_tree(
        tt: TemplateTree, relative_similarity_threshold=1
    ) -> "ContextFreeGrammar":
        """ Converts the template tree to a replacement grammar """
        if relative_similarity_threshold is None:
            relative_similarity_threshold = 1

        # = NORMALISE TT =
        tt = tt.collapse()

        # Calculate slot values
        slot_values = tt.calculated_merged_independent_slot_values(
            relative_similarity_threshold=relative_similarity_threshold
        )

        # Collapse using these calculated slot values
        tt = tt.collapse_using_slot_values(slot_values)

        # = CALCULATE GRAMMAR =

        return ContextFreeGrammar.from_slot_values(tt.get_template(), slot_values)

    @staticmethod
    def from_slot_values(
        root: Template, slot_values: SlotValues
    ) -> "ContextFreeGrammar":
        grammar: Dict[
            TemplateSlot, Collection[Template]
        ] = slot_values.get_non_replaced_mappings()

        root_elements = root.get_elements()
        if len(root_elements) == 1 and root_elements[0].is_slot():
            grammar_root = grammar[root_elements[0]]
            grammar.pop(root_elements[0])
        else:
            grammar_root = [root]

        grammar[NamedTemplateSlot("origin")] = grammar_root

        return ContextFreeGrammar(grammar)

    def get_start(self):
        return self._start

    def generate(self, slot: TemplateSlot = None, max_depth=default_depth):
        if not slot:
            slot = self._start
        if max_depth <= 0:
            return slot

        possibilities: Tuple[Template] = tuple(self._grammar[slot])
        chosen: Template = random.choice(possibilities)

        slots_to_fill = chosen.get_slots()
        slots_assignment = SlotAssignment()
        for s in slots_to_fill:
            slots_assignment[s] = self.generate(s, max_depth - 1)

        return chosen.fill(slots_assignment)

    def get_number_of_generations(self):
        return self._get_number_of_generations(self._start, dict())

    def _get_number_of_generations(
        self, slot: TemplateSlot, cache: Dict[TemplateSlot, int]
    ):
        if slot in cache:
            return cache[slot]
        total = 0
        for expansion in self._grammar[slot]:
            slots = expansion.get_slots()
            if len(slots) == 0:
                total += 1
            else:
                total += reduce(
                    (lambda x, y: x * y),
                    (self._get_number_of_generations(slot, cache) for slot in slots),
                )

        cache[slot] = total
        return total

    def generate_all(
        self, slot: TemplateSlot = None, max_depth=default_depth
    ) -> Collection[Template]:
        """ Generates all, but every time a slot occurs, it is generated again"""
        if not slot:
            slot = self._start
        return self._generate_all(slot=slot, max_depth=max_depth, cache=dict())

    def _generate_all(
        self,
        slot: TemplateSlot,
        max_depth: int,
        cache: Dict[TemplateSlot, Collection[Template]],
    ) -> Collection[Template]:
        if slot in cache:
            return cache[slot]
        if max_depth <= 0:
            return [Template([slot])]

        possibilities: Collection[Template] = self._grammar[slot]
        results = set()
        for possib in possibilities:

            slots_to_fill = possib.get_slots()
            if len(slots_to_fill) == 0:
                results.add(possib)
            else:
                slot_values = SlotValues()
                for s in slots_to_fill:
                    if s not in slot_values:
                        slot_values[s] = set(
                            self._generate_all(s, max_depth=max_depth - 1, cache=cache)
                        )

                all_content_tuples = slot_values.get_all_possible_tuples(slots_to_fill)
                for content in all_content_tuples:
                    results.add(possib.fill_with_tuple(content))

        # Cache results
        cache[slot] = results

        return results

    def generate_all_unique_slot(
        self, slot: TemplateSlot = None, max_depth=default_depth
    ) -> Collection[Template]:
        """ Generates all, but every slot with the same name is only expanded once"""
        if not slot:
            slot = self._start
        if max_depth <= 0:
            return [Template([slot])]

        possibilities: Collection[Template] = self._grammar[slot]
        results = []
        for possib in possibilities:

            slots_to_fill = possib.get_slots()
            if len(slots_to_fill) == 0:
                results.append(possib)
            else:
                slot_values = SlotValues()
                for s in slots_to_fill:
                    slot_values[s] = set(
                        self.generate_all_unique_slot(s, max_depth - 1)
                    )

                slot_assignments = slot_values.get_all_possible_assignments()
                for slot_assignment in slot_assignments:
                    results.append(possib.fill(slot_assignment))
        return results

    def generate_all_string(
        self, slot: TemplateSlot = None, max_depth=default_depth
    ) -> Collection[str]:
        return [t.to_flat_string() for t in self.generate_all(slot, max_depth)]

    def get_slots(self) -> List[TemplateSlot]:
        return list(self._grammar.keys())

    def get_size(self):
        """ Returns the length of this grammar if it was written with simple expansion rules, no disjunctions"""
        return sum(len(el) for el in self._grammar.values())

    def get_slots_sorted(self) -> List[TemplateSlot]:
        slots = self.get_slots()
        sorted_slots: List[TemplateSlot] = []
        queue = Queue()
        queue.put(self._start)
        while not queue.empty():
            element = queue.get()
            sorted_slots.append(element)

            # Only process existing keys
            if element in self._grammar:
                values = self._grammar[element]
                for template in values:
                    template_slots = template.get_slots()
                    for slot in template_slots:
                        if slot not in sorted_slots:
                            queue.put(slot)

        # Add remaining ( = unreachable slots from start)
        if len(slots) > len(sorted_slots):
            sorted_slots += set(slots) - set(sorted_slots)

        return sorted_slots

    def get_content_for(self, slot: TemplateSlot) -> Collection[Template]:
        return self._grammar[slot]

    # To string
    def __str__(self):
        return str(self.to_json())

    def __repr__(self):
        return str(self)

    def __eq__(self, other: "ContextFreeGrammar") -> bool:
        return self._grammar == other._grammar and self._start == other._start

    def is_isomorphic_with(self, other: "ContextFreeGrammar"):
        """ Returns true if they just differ in naming of the non-terminals """
        try:
            first = next(self.get_isomorphic_replacements(other))
            return first is not None
        except StopIteration:
            return False

    def get_isomorphic_replacements(
        self, other: "ContextFreeGrammar"
    ) -> Iterator[SlotReplacements]:
        """ Returns true if they just differ in naming of the non-terminals """

        # Must have same number of keys
        if len(self._grammar.keys()) == len(other._grammar.keys()):
            nt_mapping = SlotReplacements()
            for res in self._get_possible_isomorphic_nt_replacements(
                self._start, other, other._start, nt_mapping, []
            ):
                yield res

    def _get_possible_isomorphic_nt_replacements(
        self,
        non_terminal: TemplateSlot,
        other_grammar: "ContextFreeGrammar",
        other_non_terminal: TemplateSlot,
        assigned_slot_replacements: SlotReplacements,
        currently_checking: Collection[TemplateSlot],
    ) -> Iterator[SlotReplacements]:

        # Get access to expansions of the given non-terminal
        if non_terminal not in self._grammar:
            raise Exception(
                "There is no non-terminal named "
                + str(non_terminal)
                + " specified in "
                + str(self._grammar)
            )
        own_expansions = self._grammar[non_terminal]
        other_expansions = other_grammar._grammar[other_non_terminal]

        # Must have same length of expansions
        if len(own_expansions) != len(other_expansions):
            return None

        # Loop detection
        if non_terminal in currently_checking:
            yield assigned_slot_replacements
            return

        # Find all possible matches
        possible_expansions_match = _extract_possible_matches(
            own_expansions, other_expansions
        )

        # Calculate the number of possible matching expansions
        number_of_possible_matches = reduce(
            (lambda x, y: x * y),
            (len(possible_expansions_match[exp]) for exp in possible_expansions_match),
        )
        if number_of_possible_matches == 0:
            return None

        # Add the non terminal to the list to check
        this_checking = list(currently_checking)
        this_checking.append(non_terminal)

        # Check if any of the possible matching expansions are correct
        for i in range(number_of_possible_matches):

            # Pick matching expressions
            chosen_matches = _chose_matches(i, possible_expansions_match)

            # possible_new_slot_replacements = {SlotReplacements()}

            expansion_slot_replacements: Set[SlotReplacements] = {
                SlotReplacements({non_terminal: other_non_terminal})
            }

            # Check if they fit
            still_valid_matching = True
            for chosen_expansion in chosen_matches:
                other_chosen_expansion: Template = chosen_matches[chosen_expansion]

                if not chosen_expansion.has_slots():
                    continue

                # Create new possible mapping
                new_slot_replacements: SlotReplacements = SlotReplacements()

                # Extract slot replacements
                this_nt_slot_mapping = chosen_expansion.extract_content(
                    other_chosen_expansion
                )

                slots = chosen_expansion.get_slots()
                for slot_index in range(len(slots)):
                    nt = slots[slot_index]

                    # Get all slot replacements for this chosen expansion
                    expansion_slot_replacements = self._find_all_possible_slot_replacements(
                        assigned_slot_replacements,
                        this_checking,
                        expansion_slot_replacements,
                        new_slot_replacements,
                        nt,
                        other_grammar,
                        this_nt_slot_mapping[slot_index],
                    )
                    if len(expansion_slot_replacements) == 0:
                        still_valid_matching = False
                        break

                # If broken somewhere: go to next
                if not still_valid_matching:
                    break

            # Add all slot replacements if valid
            if still_valid_matching:
                for repl in expansion_slot_replacements:
                    yield repl

    def is_recursive(self) -> bool:
        """ Checks if any non-terminal could eventually map to itself """
        return self._is_recursive(self._start, [], set())

    def _is_recursive(
        self,
        slot: TemplateSlot,
        seen: Collection[TemplateSlot],
        cache: Set[TemplateSlot],
    ) -> bool:
        # If slot is already seen: return recursive
        if slot in seen:
            return True
        # If slot is already fully checked: return non-recursive
        if slot in cache:
            return False

        new_checked = list(seen) + [slot]
        expansions = self.get_content_for(slot)
        for expansion in expansions:
            for exp_slot in expansion.get_slots():
                if self._is_recursive(exp_slot, new_checked, cache):
                    return True

        cache.add(slot)
        return False

    def get_depth(self):
        """ Returns the length of the longest possible expansion """
        return self._calculate_depth(self._start, [], dict())

    def _calculate_depth(
        self,
        slot: TemplateSlot,
        seen: List[TemplateSlot],
        cache: Dict[TemplateSlot, int],
    ) -> Optional[int]:
        # If slot is already fully checked: return non-recursive
        if slot in cache:
            return cache[slot]
        # If slot is already seen, but not yet cached, it is recursive
        if slot in seen:
            return None
        seen.append(slot)

        expansions = self.get_content_for(slot)
        max_depth = max(
            max(
                (
                    self._calculate_depth(exp_slot, seen, cache)
                    for exp_slot in exp_slots
                ),
                default=0,
            )
            for exp_slots in (expansion.get_slots() for expansion in expansions)
        )

        total_depth = max_depth + 1
        cache[slot] = total_depth
        return total_depth

    def _find_all_possible_slot_replacements(
        self,
        assigned_slot_replacements: SlotReplacements,
        currently_checking: Collection[TemplateSlot],
        previous_expansion_slot_replacements: Collection[SlotReplacements],
        new_slot_replacements: SlotReplacements,
        nt: TemplateSlot,
        other_grammar: "ContextFreeGrammar",
        mapped_nt_as_template: Template,
    ) -> Set[SlotReplacements]:
        # mapped_nt_as_template: Template = this_nt_slot_mapping[nt]
        assert mapped_nt_as_template.get_number_of_elements() == 1
        mapped_nt_slot = mapped_nt_as_template.get_slots()[0]

        # Check if it already maps to something else, if so, return None
        if not assigned_slot_replacements.is_compatible_with(
            nt, mapped_nt_slot
        ) or not new_slot_replacements.is_compatible_with(nt, mapped_nt_slot):
            # still_valid = False
            return set()

        # Assign this mapping
        new_slot_replacements.add(nt, mapped_nt_slot)
        new_total_slot_replacements = new_slot_replacements.merge(
            assigned_slot_replacements
        )
        implied_slot_mappings = self._get_possible_isomorphic_nt_replacements(
            nt,
            other_grammar,
            mapped_nt_slot,
            new_total_slot_replacements,
            currently_checking,
        )
        # Merge with already decided slot replacements
        possible_new_slot_replacements = [
            implied_slot_mapping.merge(new_slot_replacements)
            for implied_slot_mapping in implied_slot_mappings
        ]
        expansion_slot_replacements = set()
        for repl in previous_expansion_slot_replacements:
            for new_repl in repl.merge_all(possible_new_slot_replacements):
                expansion_slot_replacements.add(new_repl)

        return expansion_slot_replacements

    def to_json(self):
        """ Converts the grammar to a sorted JSON string """
        converted = dict()

        for key in self.get_slots_sorted():
            values = list(val.to_flat_string() for val in self._grammar[key])
            values.sort()
            converted[key.get_name()] = values

        result = json.dumps(converted, indent=4)
        return result

    @staticmethod
    def from_json_string(string_with_dict: str):
        loaded = json.loads(string_with_dict)
        return ContextFreeGrammar.from_string(loaded)

    @staticmethod
    def from_json(string_json: Dict[str, List[str]]):
        return ContextFreeGrammar.from_string(string_json)

    @staticmethod
    def replace_modifier_variables(string_with_dict: str):
        return re.sub(_tracery_slot_modifier, r"#\g<1>#", string_with_dict)

    @staticmethod
    def from_tracery_string(string_with_dict: str):
        # Replace modifiers
        string_with_dict = ContextFreeGrammar.replace_modifier_variables(
            string_with_dict
        )

        loaded = json.loads(string_with_dict)

        # TODO: process named strings!
        if re.search(_tracery_specifiers_regex, string_with_dict) is not None:
            raise ValueError("The parser can not deal with saving values right now")

        return ContextFreeGrammar.from_string(loaded, _tracery_template_parser)


_tracery_slot_regex = re.compile(r"#([a-zA-Z0-9_-]+)#")
_tracery_slot_modifier = re.compile(r"#([a-zA-Z0-9_-]+)\.[a-zA-Z0-9_-]+#")
_tracery_specifiers_regex = re.compile(r"\[([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)\]")


def _tracery_template_parser(input: str) -> Template:
    return Template.from_string(input, _tracery_slot_regex)


def _chose_matches(i, possible_expansions_match):
    chosen_matches: Dict[Template, Template] = dict()
    index = i
    for exp in possible_expansions_match:
        possible = possible_expansions_match[exp]
        len_possible = len(possible)
        chosen_match_idx = int(index % len_possible)
        chosen_matches[exp] = possible[chosen_match_idx]
        index = index / len_possible
    return chosen_matches


def _extract_possible_matches(
    own_expansions, other_expansions
) -> Dict[Template, List[Template]]:
    possible_expansions_match: Dict[Template, List[Template]] = dict()
    for own_expansion in own_expansions:
        possible_expansions_match[own_expansion] = []
        for other_expansion in other_expansions:
            # Check if they cover each other
            if (
                own_expansion.has_same_shape(other_expansion)
                and other_expansion not in possible_expansions_match[own_expansion]
            ):
                possible_expansions_match[own_expansion].append(other_expansion)
    return possible_expansions_match
