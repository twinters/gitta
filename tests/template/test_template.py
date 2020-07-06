import random
import unittest
from typing import List

from src.slot_values import SlotValues
from src.template import Template
from src.template_elements import (
    TemplateString,
    TemplateSlot,
    NamedTemplateSlot,
    SlotAssignment,
)


class TemplateTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(123)

        self.a = TemplateString("a")
        self.b = TemplateString("b")
        self.c = TemplateString("c")
        self.slot1 = TemplateSlot()
        self.slot2 = TemplateSlot()
        self.slot_x = NamedTemplateSlot("x")
        self.slot_y = NamedTemplateSlot("y")
        self.slot_z = NamedTemplateSlot("z")

        self.at = Template([self.a])
        self.bt = Template([self.b])
        self.ct = Template([self.c])

    def test_from_string(self):
        original_string = "a b c d"
        template = Template.from_string(original_string)
        self.assertEqual(4, template.get_number_of_elements())
        self.assertEqual(original_string, template.to_flat_string())

    def test_slot_parsing(self):
        original_string = "a [SLOT] c d"
        template = Template.from_string(original_string, slot_token="[SLOT]")
        self.assertEqual(4, template.get_number_of_elements())
        self.assertFalse(template._elements[0].is_slot())
        self.assertTrue(template._elements[1].is_slot())
        self.assertFalse(template._elements[2].is_slot())
        self.assertFalse(template._elements[3].is_slot())

    def test_named_slot_parsing(self):
        original_string = "a <A> c d <B>"
        template = Template.from_string(original_string)

        self.assertEqual(
            Template(
                [
                    TemplateString("a"),
                    NamedTemplateSlot("A"),
                    TemplateString("c"),
                    TemplateString("d"),
                    NamedTemplateSlot("B"),
                ]
            ),
            template,
        )

    def test_named_slot_parsing_end(self):
        original_string = "a <A> c d <B> e"
        template = Template.from_string(original_string)

        self.assertEqual(
            Template(
                [
                    TemplateString("a"),
                    NamedTemplateSlot("A"),
                    TemplateString("c"),
                    TemplateString("d"),
                    NamedTemplateSlot("B"),
                    TemplateString("e"),
                ]
            ),
            template,
        )

    def test_covers_string(self):
        slotted_template_string = "a b [SLOT] d"
        template = Template.from_string(slotted_template_string, slot_token="[SLOT]")

        # True covers
        self.assertTrue(template.covers_string("a b c d"))
        self.assertTrue(template.covers_string("a b c e d"))
        self.assertTrue(template.covers_string("a b c e f d"))
        self.assertTrue(template.covers_string("a b c d d"))

        self.assertTrue(template.covers_string("a b d"))
        self.assertTrue(template.covers_string("a b d d d d"))

        # Not covers
        self.assertFalse(template.covers_string("a a d d"))
        self.assertFalse(template.covers_string("a b d c"))
        self.assertFalse(template.covers_string("a b c"))
        self.assertFalse(template.covers_string("d"))

    def test_covers_slotted(self):
        slotted_template_string = "a b [SLOT] d"
        template = Template.from_string(slotted_template_string, slot_token="[SLOT]")

        def covers_slotted(slotted_string):
            return template.covers(
                Template.from_string(slotted_string, slot_token="[SLOT]")
            )

        # True covers
        self.assertTrue(covers_slotted("a b [SLOT] d"))
        self.assertTrue(covers_slotted("a b [SLOT] [SLOT] d"))

        # Not covers
        self.assertFalse(covers_slotted("[SLOT]"))
        self.assertFalse(covers_slotted("a [SLOT] [SLOT] d"))
        self.assertFalse(covers_slotted("[SLOT] [SLOT] [SLOT] [SLOT]"))
        self.assertFalse(covers_slotted("a b c d [SLOT]"))
        self.assertFalse(covers_slotted("a b d [SLOT]"))
        self.assertFalse(covers_slotted("[SLOT] a b c d"))
        self.assertFalse(covers_slotted("[SLOT] a b d"))
        self.assertFalse(covers_slotted("a b [SLOT] d [SLOT]"))

    def test_merge_string(self):
        self.assertEqual("a [SLOT] c d", calculate_merged_string("a b c d", "a e c d"))
        self.assertEqual("a [SLOT] c d", calculate_merged_string("a b c d", "a c c d"))
        self.assertEqual("a [SLOT] c d", calculate_merged_string("a b c d", "a c d"))
        self.assertEqual(
            "a [SLOT] c d", calculate_merged_string("a b c d", "a f f c d")
        )
        self.assertEqual("a [SLOT] d", calculate_merged_string("a b c d", "a e f d"))
        self.assertEqual(
            "Hallo [SLOT] , hoe gaat het [SLOT] ?",
            calculate_merged_string(
                "Hallo , hoe gaat het met jou ?", "Hallo daar , hoe gaat het ?"
            ),
        )
        self.assertEqual(
            "Hallo [SLOT] , hoe gaat het [SLOT] ?",
            calculate_merged_string(
                "Hallo daar , hoe gaat het ?", "Hallo , hoe gaat het met jou ?"
            ),
        )

    def test_merge(self):
        self.assertEqual(
            "a [SLOT] c [SLOT] e",
            calculate_merged_string("a b c [SLOT] e", "a d c e e"),
        )
        self.assertEqual(
            "a [SLOT] c [SLOT] e",
            calculate_merged_string("a b c [SLOT] e", "a d c [SLOT] e"),
        )
        self.assertEqual(
            "a [SLOT] e", calculate_merged_string("a b c [SLOT] e", "a d [SLOT] e")
        )

    def test_merge_exists(self):
        self.assertTrue(calculate_merged_string("a [SLOT]", "[SLOT] a") in {"[SLOT]", "[SLOT] [SLOT]"})

    def test_merge_named_slots(self):
        self.assertEqual(
            "a [SLOT] <A> e", calculate_merged_string("a b <A> e", "a c <A> e"),
        )
        self.assertEqual(
            "<X> [SLOT]", calculate_merged_string("<X> a b", "<X> c"),
        )

    def test_merge_all(self):
        t1 = Template([self.slot_x, self.a, self.b])
        t2 = Template([self.slot_x, self.a, self.slot_y])
        t3 = Template([self.slot_x, self.c])

        t12 = Template([self.slot_x, self.a, self.slot1])
        self.assertEqual(t12, Template.merge_all([t1, t2]))
        self.assertEqual(t12, Template.merge_all([t1, t2], t12))

        t123 = Template([self.slot_x, self.slot1])
        self.assertEqual(t123, Template.merge_all([t12, t3]))
        self.assertEqual(t123, Template.merge_all([t12, t3], t123))
        self.assertEqual(t123, Template.merge_all([t3, t12]))
        self.assertEqual(t123, Template.merge_all([t3, t12], t123))

        self.assertEqual(t123, Template.merge_all([t1, t2, t3]))
        self.assertEqual(t123, Template.merge_all([t1, t2, t3], t123))
        self.assertEqual(t123, Template.merge_all([t3, t2, t1]))
        self.assertEqual(t123, Template.merge_all([t3, t2, t1], t123))

    def test_extract_content_small(self):
        self.assertEqual(
            _to_templates([]),
            Template.from_string("").extract_content(Template.from_string("")),
        )
        self.assertEqual(
            _to_templates([""]),
            Template.from_string("[SLOT]").extract_content(Template.from_string("")),
        )
        self.assertEqual(
            _to_templates(["", "", ""]),
            Template.from_string("[SLOT] [SLOT] [SLOT]").extract_content(
                Template.from_string("")
            ),
        )
        self.assertEqual(
            _to_templates(["a"]),
            Template.from_string("[SLOT]").extract_content(Template.from_string("a")),
        )
        self.assertEqual(
            _to_templates(["[SLOT]"]),
            Template.from_string("[SLOT]").extract_content(
                Template.from_string("[SLOT]")
            ),
        )

    def test_extract_content_one(self):
        b1 = Template.from_string("a [SLOT]", slot_token="[SLOT]")
        t1 = Template.from_string("a 1")
        self.assertEqual(_to_templates(["1"]), b1.extract_content(t1))
        b2 = Template.from_string("[SLOT] c", slot_token="[SLOT]")
        t2 = Template.from_string("2 c")
        self.assertEqual(_to_templates(["2"]), b2.extract_content(t2))

        b3 = Template.from_string("a [SLOT] c", slot_token="[SLOT]")
        t3 = Template.from_string("a 3 c")
        self.assertEqual(_to_templates(["3"]), b3.extract_content(t3))
        self.assertEqual(_to_templates(["3 c"]), b1.extract_content(t3))
        self.assertEqual(_to_templates(["a 3"]), b2.extract_content(t3))

    def test_extract_content_two(self):
        b1 = Template.from_string("a [SLOT] c [SLOT] e", slot_token="[SLOT]")
        t1 = Template.from_string("a b c d e")
        self.assertEqual(_to_templates(["b", "d"]), b1.extract_content(t1))
        t1 = Template.from_string("a b b c d e")
        self.assertEqual(_to_templates(["b b", "d"]), b1.extract_content(t1))

    def test_extract_content_all_ambiguous(self):
        b1 = Template.from_string("[SLOT] [SLOT]", slot_token="[SLOT]")
        t1 = Template.from_string("a b")
        self.assertEqual(
            {
                _to_templates(["a", "b"]),
                _to_templates(["a b", ""]),
                _to_templates(["", "a b"]),
            },
            b1.extract_content_all(t1),
        )

        # With lowest slot length variance should be picked:
        self.assertEqual(_to_templates(["a", "b"]), b1.extract_content(t1))

    def test_extract_content_all_ambiguous_2(self):
        b2 = Template.from_string("a [SLOT] a [SLOT]", slot_token="[SLOT]")
        t2 = Template.from_string("a a a a")
        self.assertEqual(
            {
                _to_templates(["", "a a"]),
                _to_templates(["a a", ""]),
                _to_templates(["a", "a"]),
            },
            b2.extract_content_all(t2),
        )

        # With lowest slot length variance should be picked:
        self.assertEqual(_to_templates(["a", "a"]), b2.extract_content(t2))

    def test_fill(self):
        a = self.a
        b = self.b
        c = self.c
        slot1 = self.slot1
        slot2 = self.slot2

        self.assertEqual(
            Template.from_string("b"),
            Template([slot1]).fill(SlotAssignment({slot1: Template([b])})),
        )
        self.assertEqual(
            Template.from_string("a b"),
            Template([a, slot1]).fill(SlotAssignment({slot1: Template([b])})),
        )
        self.assertEqual(
            Template.from_string("a b c"),
            Template([a, slot1, c]).fill(SlotAssignment({slot1: Template([b])})),
        )
        self.assertEqual(
            Template.from_string("a b c a"),
            Template([a, slot1, c, slot2]).fill(
                SlotAssignment({slot1: Template([b]), slot2: Template([a])})
            ),
        )
        self.assertEqual(
            Template.from_string("a b a c"),
            Template([a, slot1, slot2, c]).fill(
                SlotAssignment({slot1: Template([b]), slot2: Template([a])})
            ),
        )
        self.assertEqual(
            Template.from_string("a b a c"),
            Template([a, slot1, slot2, c]).fill(
                SlotAssignment({slot2: Template([a]), slot1: Template([b])})
            ),
        )
        self.assertEqual(
            Template.from_string("a b a c"),
            Template([a, slot1, slot2, c]).fill_with_strings(["b", "a"]),
        )

    def test_named_slots(self):

        self.assertEqual(
            Template([self.slot_x]),
            Template([self.slot1]).name_template_slots({self.slot1: self.slot_x}),
        )
        self.assertEqual(
            Template([self.slot_x, self.a, self.slot_y]),
            Template([self.slot1, self.a, self.slot2]).name_template_slots(
                {self.slot1: self.slot_x, self.slot2: self.slot_y}
            ),
        )
        self.assertEqual(
            Template([self.slot_x, self.a, self.slot_x]),
            Template([self.slot1, self.a, self.slot2]).name_template_slots(
                {self.slot1: self.slot_x, self.slot2: self.slot_x}
            ),
        )

    def test_encompasses(self):
        template_1 = Template([self.slot_x, self.a, self.slot_y])
        template_2 = Template([self.slot_x, self.a, self.b])
        template_3 = Template([self.c, self.a, self.b])
        template_4 = Template([self.slot_z, self.a, self.b])

        self.assertTrue(
            template_1.encompasses(
                template_1,
                SlotValues(
                    {
                        self.slot_x: [Template([self.slot_x])],
                        self.slot_y: [Template([self.slot_y])],
                    }
                ),
            )
        )
        self.assertTrue(
            template_1.encompasses(
                template_2,
                SlotValues(
                    {
                        self.slot_x: [Template([self.slot_x])],
                        self.slot_y: [Template([self.b])],
                    }
                ),
            )
        )
        self.assertTrue(
            template_1.encompasses(
                template_3,
                SlotValues(
                    {
                        self.slot_x: [Template([self.c])],
                        self.slot_y: [Template([self.b])],
                    }
                ),
            )
        )
        self.assertTrue(
            template_1.encompasses(
                template_4,
                SlotValues(
                    {
                        self.slot_x: [Template([self.slot_z])],
                        self.slot_y: [Template([self.b])],
                    }
                ),
            )
        )
        self.assertFalse(
            template_1.encompasses(
                template_2,
                SlotValues(
                    {
                        self.slot_x: [Template([self.slot_x])],
                        self.slot_y: [Template([self.a])],
                    }
                ),
            )
        )

    def test_get_slot_values(self):
        t1 = Template([self.a, self.slot_x, self.a, self.slot_y, self.a, self.slot_z])
        t2 = Template([self.a, self.b, self.a, self.b, self.a, self.b])
        t3 = Template([self.a, self.c, self.a, self.b, self.a, self.c])
        tc = Template([self.a, self.c, self.a, self.c, self.a, self.c])
        ta = Template([self.a, self.a, self.a, self.a, self.a, self.a])

        self.assertEqual(
            {self.slot_x: {self.bt}, self.slot_y: {self.bt}, self.slot_z: {self.bt}},
            t1.get_slot_values([t2]),
        )

        self.assertEqual(
            {
                self.slot_x: {self.bt, self.ct},
                self.slot_y: {self.bt},
                self.slot_z: {self.bt, self.ct},
            },
            t1.get_slot_values([t2, t3]),
        )
        self.assertEqual(
            {
                self.slot_x: {self.bt, self.ct},
                self.slot_y: {self.bt, self.ct},
                self.slot_z: {self.bt, self.ct},
            },
            t1.get_slot_values([t2, t3, tc]),
        )
        self.assertEqual(
            {
                self.slot_x: {self.at, self.bt, self.ct},
                self.slot_y: {self.at, self.bt, self.ct},
                self.slot_z: {self.at, self.bt, self.ct},
            },
            t1.get_slot_values([t2, t3, tc, ta]),
        )
        self.assertEqual(
            {
                self.slot_x: {self.at, self.ct},
                self.slot_y: {self.at, self.ct},
                self.slot_z: {self.at, self.ct},
            },
            t1.get_slot_values([tc, ta]),
        )

    def test_get_slot_values_same_slot_name(self):
        t1 = Template([self.a, self.slot_x, self.a, self.slot_y, self.a, self.slot_x])
        t2 = Template([self.a, self.b, self.a, self.b, self.a, self.c])

        self.assertEqual(
            {self.slot_x: {self.bt, self.ct}, self.slot_y: {self.bt}},
            t1.get_slot_values([t2]),
        )


def _to_templates(strings: List[str]):
    return tuple([Template.from_string(s) for s in strings])


def calculate_merged_string(string1, string2):
    merged_templates = Template.merge_templates_wagner_fischer(
        Template.from_string(string1, slot_token="[SLOT]"),
        Template.from_string(string2, slot_token="[SLOT]"),
        allow_longer_template=False
    )
    return next(merged_templates).to_flat_string(detokenizer=lambda x: " ".join(x))


if __name__ == "__main__":
    unittest.main()
