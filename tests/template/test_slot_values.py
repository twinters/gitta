import random
import unittest
from typing import List, Collection, Set, Tuple

from gitta.slot_name_generator import alphabetic_slot_name_iterator
from gitta.slot_values import SlotValues
from gitta.template import Template

from gitta.hashabledict import hashabledict
from gitta.template_elements import TemplateString, NamedTemplateSlot, SlotAssignment


class SlotValuesTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(123)

        self.a = NamedTemplateSlot("A")
        self.b = NamedTemplateSlot("B")
        self.c = NamedTemplateSlot("C")
        self.d = NamedTemplateSlot("D")

        self.e1 = Template([TemplateString("hello")])
        self.e2 = Template([TemplateString("hi")])
        self.e3 = Template([TemplateString("hey")])
        self.e12 = {self.e1, self.e2}
        self.e23 = {self.e2, self.e3}
        self.e123 = {self.e1, self.e2, self.e3}

        self.e4 = Template([TemplateString("world")])
        self.e5 = Template([TemplateString("earth")])
        self.e6 = Template([TemplateString("everyone")])
        self.e456 = {self.e4, self.e5, self.e6}

    def test_get_all_slot_assignments(self):
        slot_values = SlotValues(
            {self.a: {Template([self.c]), self.e1}, self.c: self.e12}
        )
        self.assertEqual(
            {SlotAssignment({self.c: self.e1}), SlotAssignment({self.c: self.e2})},
            set(slot_values.get_all_possible_assignments([self.c])),
        )

    def test_merge_basic(self):
        slot_values = SlotValues(
            {self.a: self.e123, self.b: self.e123, self.c: self.e456}
        )

        merged = slot_values.merge_slots()

        self.assertEqual(hashabledict({self.b: self.a}), merged.get_replacements())
        self.assertEqual(
            SlotValues(
                {self.a: self.e123, self.b: {Template([self.a])}, self.c: self.e456}
            ),
            merged,
        )

    def test_merge_small_overlap(self):
        slot_values = SlotValues({self.a: self.e12, self.b: self.e23})

        merged = slot_values.merge_slots(relative_similarity_threshold=0.3)

        self.assertEqual(hashabledict({self.b: self.a}), merged.get_replacements())
        self.assertEqual(
            SlotValues({self.a: self.e123, self.b: {Template([self.a])}}), merged,
        )

    def test_merge_containing_slot(self):
        slot_values = SlotValues(
            {
                self.a: {Template([self.b]), self.e1, self.e2, self.e3},
                self.b: self.e123,
                self.c: self.e456,
            }
        )

        merged = slot_values.merge_slots()

        self.assertEqual(hashabledict({self.a: self.b}), merged.get_replacements())
        self.assertEqual(
            SlotValues(
                {self.a: {Template([self.b])}, self.b: self.e123, self.c: self.e456}
            ),
            merged,
        )

    def test_merge_containing_slot_second(self):
        slot_values = SlotValues(
            {
                self.a: {Template([self.c]), self.e1, self.e2, self.e3},
                self.b: self.e123,
                self.c: self.e123,
            }
        )

        merged = slot_values.merge_slots()

        self.assertEqual(
            hashabledict({self.a: self.b, self.c: self.b}), merged.get_replacements()
        )
        self.assertEqual(
            SlotValues(
                {
                    self.a: {Template([self.b])},
                    self.b: self.e123,
                    self.c: {Template([self.b])},
                }
            ),
            merged,
        )

    def test_merge_containing_multiple_slot(self):
        slot_values = SlotValues(
            {
                self.a: {Template([self.b]), Template([self.c]), self.e1, self.e2},
                self.b: self.e123,
                self.c: self.e12,
            }
        )

        merged = slot_values.merge_slots()

        self.assertEqual(hashabledict({self.a: self.b}), merged.get_replacements())
        self.assertEqual(
            SlotValues(
                {self.a: {Template([self.b])}, self.b: self.e123, self.c: self.e12}
            ),
            merged,
        )

    def test_merge_containing_multiple_slots_complely(self):
        slot_values = SlotValues(
            {
                self.a: {Template([self.b]), Template([self.c]), self.e1, self.e2},
                self.b: self.e123,
                self.c: self.e123,
            }
        )

        merged = slot_values.merge_slots()

        self.assertEqual(
            hashabledict({self.a: self.b, self.c: self.b}), merged.get_replacements()
        )
        self.assertEqual(
            SlotValues(
                {
                    self.a: {Template([self.b])},
                    self.b: self.e123,
                    self.c: {Template([self.b])},
                }
            ),
            merged,
        )

    def test_merge_relative_overlap_values(self):
        contents = _create_contents(10)
        slot_values = SlotValues(
            {self.a: set(contents), self.b: _shuffled_subset(contents, 0, 2),}
        )

        # It should not merge if the relative similarity threshold is > 0.2
        merged_none = slot_values.merge_slots()
        self.assertEqual(slot_values, merged_none)

        merged_1 = slot_values.merge_slots(relative_similarity_threshold=1)
        self.assertEqual(slot_values, merged_1)

        merged_09 = slot_values.merge_slots(relative_similarity_threshold=0.9)
        self.assertEqual(slot_values, merged_09)

        merged_05 = slot_values.merge_slots(relative_similarity_threshold=0.5)
        self.assertEqual(slot_values, merged_05)

        # B should merge into A if the threshold is <= 0.2
        expected_merged = SlotValues(
            {self.a: set(contents), self.b: {Template([self.a])}}
        )

        merged_02 = slot_values.merge_slots(relative_similarity_threshold=0.2)
        self.assertEqual(expected_merged, merged_02)

        merged_01 = slot_values.merge_slots(relative_similarity_threshold=0.1)
        self.assertEqual(expected_merged, merged_01)

    def test_merge_relative_overlap_values_three_variables_1(self):
        contents = _create_contents(10)
        slot_values = SlotValues(
            {
                self.a: set(contents),
                self.b: set(contents[0:2]),
                self.c: set(contents[5:8]),
            }
        )

        # It should not merge if the relative similarity threshold is > 0.2
        merged_none = slot_values.merge_slots()
        self.assertEqual(slot_values, merged_none)

        merged_1 = slot_values.merge_slots(relative_similarity_threshold=1)
        self.assertEqual(slot_values, merged_1)

        merged_05 = slot_values.merge_slots(relative_similarity_threshold=0.5)
        self.assertEqual(slot_values, merged_05)

        merged_03 = slot_values.merge_slots(relative_similarity_threshold=0.3)
        self.assertEqual(
            SlotValues(
                {
                    self.a: set(contents),
                    self.b: set(contents[0:2]),
                    self.c: {Template([self.a])},
                }
            ),
            merged_03,
        )

        # B should merge into A if the threshold is <= 0.2
        full_merge = SlotValues(
            {
                self.a: set(contents),
                self.b: {Template([self.a])},
                self.c: {Template([self.a])},
            }
        )

        merged_02 = slot_values.merge_slots(relative_similarity_threshold=0.2)
        self.assertEqual(full_merge, merged_02)

        merged_01 = slot_values.merge_slots(relative_similarity_threshold=0.1)
        self.assertEqual(full_merge, merged_01)

    def test_merge_relative_overlap_values_three_variables_2(self):
        contents = _create_contents(10)
        slot_values = SlotValues(
            {
                self.a: set(contents[1:5]),
                self.b: set(contents[0:2]),
                self.c: set(contents[2:6]),
            }
        )

        # It should not merge if the relative similarity threshold is > 0.2
        merged_none = slot_values.merge_slots()
        self.assertEqual(slot_values, merged_none)

        merged_1 = slot_values.merge_slots(relative_similarity_threshold=1)
        self.assertEqual(slot_values, merged_1)

        merged_061 = slot_values.merge_slots(relative_similarity_threshold=0.61)
        self.assertEqual(slot_values, merged_061)

        expected_first_merged = SlotValues(
            {
                self.a: set(contents[1:6]),
                self.b: set(contents[0:2]),
                self.c: {Template([self.a])},
            }
        )

        merged_06 = slot_values.merge_slots(relative_similarity_threshold=0.6)
        self.assertEqual(
            expected_first_merged, merged_06,
        )

        merged_021 = slot_values.merge_slots(relative_similarity_threshold=0.21)
        self.assertEqual(
            expected_first_merged, merged_021,
        )

        expected_full_merged = SlotValues(
            {
                self.a: set(contents[0:6]),
                self.b: {Template([self.a])},
                self.c: {Template([self.a])},
            }
        )
        merged_02 = slot_values.merge_slots(relative_similarity_threshold=0.2)
        self.assertEqual(
            expected_full_merged, merged_02,
        )
        merged_01 = slot_values.merge_slots(relative_similarity_threshold=0.1)
        self.assertEqual(
            expected_full_merged, merged_01,
        )

    def test_merge_large(self):
        contents = _create_contents(100)
        slot_values = SlotValues(
            {
                NamedTemplateSlot("a"): set(contents[0:2]),
                NamedTemplateSlot("b"): set(contents[2:4]),
                NamedTemplateSlot("c"): set(contents[4:6]),
                NamedTemplateSlot("d"): set(contents[6:8]),
                NamedTemplateSlot("e"): set(contents[8:10]),
                NamedTemplateSlot("f"): set(contents[10:12]),
                NamedTemplateSlot("g"): set(contents[12:14]),
                NamedTemplateSlot("h"): set(contents[14:16]),
                NamedTemplateSlot("i"): set(contents[16:18]),
                NamedTemplateSlot("j"): set(contents[18:20]),
                NamedTemplateSlot("k"): set(contents[20:22]),
                NamedTemplateSlot("l"): set(contents[22:24]),
                NamedTemplateSlot("m"): set(contents[24:26]),
                NamedTemplateSlot("n"): set(contents[26:28]),
                NamedTemplateSlot("o"): set(contents[28:30]),
                NamedTemplateSlot("p"): set(contents[30:32]),
                NamedTemplateSlot("q"): set(contents[32:34]),
                NamedTemplateSlot("r"): set(contents[34:36]),
                NamedTemplateSlot("s"): set(contents[36:38]),
                NamedTemplateSlot("t"): set(contents[38:40]),
                NamedTemplateSlot("u"): set(contents[40:42]),
                NamedTemplateSlot("v"): set(contents[42:44]),
                NamedTemplateSlot("w"): set(contents[44:46]),
                NamedTemplateSlot("x"): set(contents[46:48]),
                NamedTemplateSlot("y"): set(contents[48:50]),
                NamedTemplateSlot("z"): set(contents[50:52]),
            }
        )
        self.assertEqual(slot_values, slot_values.merge_slots())
        self.assertEqual(slot_values, slot_values.merge_slots(0.1))
        self.assertEqual(slot_values, slot_values.merge_slots(0.001))

        # Now add something that overlaps
        extra_slot_1 = NamedTemplateSlot("zzz-extra")
        slot_values[extra_slot_1] = set(contents[0:9])
        self.assertEqual(slot_values, slot_values.merge_slots())

        merged_011 = slot_values.merge_slots(0.112)
        self.assertEqual(set(contents[0:9]), merged_011[NamedTemplateSlot("a")])
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged_011[NamedTemplateSlot("b")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged_011[NamedTemplateSlot("c")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged_011[NamedTemplateSlot("d")]
        )
        self.assertEqual({Template([NamedTemplateSlot("a")])}, merged_011[extra_slot_1])
        self.assertEqual(
            set(contents[8:10]), merged_011[NamedTemplateSlot("e")],
        )

        merged_01 = slot_values.merge_slots(0.1)
        self.assertEqual(set(contents[0:10]), merged_01[NamedTemplateSlot("a")])
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged_01[NamedTemplateSlot("d")]
        )
        self.assertEqual({Template([NamedTemplateSlot("a")])}, merged_011[extra_slot_1])
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged_01[NamedTemplateSlot("e")]
        )

        extra_slot_2 = NamedTemplateSlot("zzz-extra-2")
        slot_values[extra_slot_2] = set(contents[11:52])
        self.assertEqual(slot_values, slot_values.merge_slots())

        merged2_005 = slot_values.merge_slots(0.05)
        self.assertEqual(set(contents[0:10]), merged2_005[NamedTemplateSlot("a")])
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_005[NamedTemplateSlot("d")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_005[extra_slot_1]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_005[NamedTemplateSlot("e")]
        )
        self.assertEqual(set(contents[11:52]), merged2_005[extra_slot_2])
        self.assertEqual(set(contents[10:12]), merged2_005[NamedTemplateSlot("f")])
        self.assertEqual(set(contents[14:16]), merged2_005[NamedTemplateSlot("h")])

        merged2_0023 = slot_values.merge_slots(0.023)
        self.assertEqual(set(contents[0:10]), merged2_0023[NamedTemplateSlot("a")])
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_0023[NamedTemplateSlot("d")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_0023[extra_slot_1]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("a")])}, merged2_0023[NamedTemplateSlot("e")]
        )
        self.assertEqual(set(contents[10:52]), merged2_0023[NamedTemplateSlot("f")])
        self.assertEqual(
            {Template([NamedTemplateSlot("f")])}, merged2_0023[NamedTemplateSlot("g")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("f")])}, merged2_0023[NamedTemplateSlot("h")]
        )
        self.assertEqual(
            {Template([NamedTemplateSlot("f")])}, merged2_0023[extra_slot_2]
        )

        extra_slot_3 = NamedTemplateSlot("zzz-extra-3")
        slot_values[extra_slot_3] = set(contents[9:11])
        self.assertEqual(slot_values, slot_values.merge_slots())
        a = {Template([NamedTemplateSlot("a")])}
        self.assertEqual(
            SlotValues(
                {
                    NamedTemplateSlot("a"): set(contents[0:52]),
                    NamedTemplateSlot("b"): a,
                    NamedTemplateSlot("c"): a,
                    NamedTemplateSlot("d"): a,
                    NamedTemplateSlot("e"): a,
                    NamedTemplateSlot("f"): a,
                    NamedTemplateSlot("g"): a,
                    NamedTemplateSlot("h"): a,
                    NamedTemplateSlot("i"): a,
                    NamedTemplateSlot("j"): a,
                    NamedTemplateSlot("k"): a,
                    NamedTemplateSlot("l"): a,
                    NamedTemplateSlot("m"): a,
                    NamedTemplateSlot("n"): a,
                    NamedTemplateSlot("o"): a,
                    NamedTemplateSlot("p"): a,
                    NamedTemplateSlot("q"): a,
                    NamedTemplateSlot("r"): a,
                    NamedTemplateSlot("s"): a,
                    NamedTemplateSlot("t"): a,
                    NamedTemplateSlot("u"): a,
                    NamedTemplateSlot("v"): a,
                    NamedTemplateSlot("w"): a,
                    NamedTemplateSlot("x"): a,
                    NamedTemplateSlot("y"): a,
                    NamedTemplateSlot("z"): a,
                    extra_slot_1: a,
                    extra_slot_2: a,
                    extra_slot_3: a,
                }
            ),
            slot_values.merge_slots(0.01),
        )

    def test_merge_superlarge(self):
        nb_template_elements = 1000
        slot_values, contents = _create_large_slotvalues(
            nb_template_elements=nb_template_elements,
            nb_slots=5000,
            max_elements_per_slot=20,
        )
        merged = slot_values.merge_slots(relative_similarity_threshold=0.001)
        # print(merged)

        first_slot = list(merged.keys())[0]
        self.assertEqual(set(contents), merged[first_slot])
        for slot in merged:
            if slot is not first_slot:
                self.assertEqual({Template([first_slot])}, merged[slot])


def _create_contents(max_number: int) -> List[Template]:
    return [Template([TemplateString(str(i))]) for i in range(max_number)]


def _create_large_slotvalues(
    nb_template_elements: int, nb_slots: int, max_elements_per_slot: int
) -> Tuple[SlotValues, List[Template]]:
    contents = _create_contents(nb_template_elements)
    slot_generator = (NamedTemplateSlot(s) for s in alphabetic_slot_name_iterator())
    slot_values = SlotValues()
    for i in range(nb_slots):
        slot_values[next(slot_generator)] = _shuffled_subset(
            contents, 0, random.randint(1, max_elements_per_slot)
        )
    return slot_values, contents


def _shuffled_subset(
    col: Collection[Template], min_index=0, max_index=None
) -> Set[Template]:
    if max_index is None:
        max_index = len(col)
    lst = list(col)
    random.shuffle(lst)
    return set(lst[min_index:max_index])


if __name__ == "__main__":
    unittest.main()
