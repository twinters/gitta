import random
import unittest

from gitta.slot_values import SlotValues
from gitta.template import Template
from gitta.template_elements import TemplateString, NamedTemplateSlot, SlotAssignment
from gitta.template_tree import TemplateTree
from gitta.template_tree_learner import visualise_template_tree_history
from gitta.template_tree_visualiser import render_tree_string


class TemplateTreeLearner(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(123)
        self.s1 = TemplateTree(Template.from_string("a b c d"))
        self.s2 = TemplateTree(Template.from_string("a b e d"))
        self.s3 = TemplateTree(Template.from_string("a b f d"))
        self.s4 = TemplateTree(Template.from_string("g b h d"))
        self.s5 = TemplateTree(Template.from_string("h i j d"))
        self.all_s = [self.s1, self.s2, self.s3, self.s4, self.s5]

        # Uncompressed tree (one of multiple possible)
        self.u1 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"),
            [self.s1, self.s2],
        )
        self.u2 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"),
            [self.s3, self.u1],
        )
        self.u3 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"),
            [self.s4, self.u2],
        )
        self.u4 = TemplateTree(
            Template.from_string("[SLOT] d", slot_token="[SLOT]"), [self.s5, self.u3]
        )

        # Collapsed tree
        self.t1 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"),
            [self.s1, self.s2, self.s3],
        )
        self.t2 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"),
            [self.s4, self.t1],
        )
        self.t3 = TemplateTree(
            Template.from_string("[SLOT] d", slot_token="[SLOT]"), [self.s5, self.t2]
        )

    def test_reduce_depth(self):
        # Depth 1
        u4_reduced_1 = self.u4.reduce_depth(1)
        self.assertEqual(1, u4_reduced_1.get_depth())
        self.assertEqual(
            TemplateTree(
                self.u4.get_template(), [self.s1, self.s2, self.s3, self.s4, self.s5]
            ),
            u4_reduced_1,
        )

        # Depth 2
        u4_reduced_2 = self.u4.reduce_depth(2)
        self.assertEqual(2, u4_reduced_2.get_depth())
        self.assertEqual(
            TemplateTree(self.u4.get_template(), [self.u1, self.s3, self.s4, self.s5]),
            u4_reduced_2,
        )

        # Depth 3
        u4_reduced_3 = self.u4.reduce_depth(3)
        self.assertEqual(3, u4_reduced_3.get_depth())
        self.assertEqual(
            TemplateTree(self.u4.get_template(), [self.u2, self.s4, self.s5]),
            u4_reduced_3,
        )

        # Depth 4
        u4_reduced_4 = self.u4.reduce_depth(4)
        self.assertEqual(4, u4_reduced_4.get_depth())
        self.assertEqual(
            TemplateTree(self.u4.get_template(), [self.u3, self.s5]), u4_reduced_4,
        )

        # T Tree
        t3_reduced_1 = self.t3.reduce_depth(1)
        self.assertEqual(1, t3_reduced_1.get_depth())
        self.assertEqual(
            TemplateTree(
                self.t3.get_template(), [self.s1, self.s2, self.s3, self.s4, self.s5]
            ),
            t3_reduced_1,
        )

        # T Tree Depth 2
        t3_reduced_2 = self.t3.reduce_depth(2)
        self.assertEqual(2, t3_reduced_2.get_depth())
        self.assertEqual(
            TemplateTree(self.t3.get_template(), [self.t1, self.s4, self.s5]),
            t3_reduced_2,
        )

    def test_collapse(self):
        """ Test if collapsing a tree gives the desired result """

        # For top level of a node
        self.assertEqual(self.t1, self.u2.collapse())

        # Bit lower
        self.assertEqual(self.t2, self.u3.collapse())

        # For full tree
        collapsed_u4 = self.u4.collapse()
        t3 = self.t3
        self.assertEqual(self.t3, collapsed_u4)

    def test_collapse_same_children(self):
        """ Tests if collapsing a tree with children with similar templates will merge correctly """
        ss1 = TemplateTree(Template.from_string("a b c c d"))
        ss2 = TemplateTree(Template.from_string("c b e e d"))
        ss3 = TemplateTree(Template.from_string("h h h b f d"))
        ss4 = TemplateTree(Template.from_string("i i i b g d"))
        ss5 = TemplateTree(Template.from_string("j k l l d"))

        us1 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"), [ss1, ss2]
        )
        us2 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"), [ss3, ss4]
        )
        us3 = TemplateTree(
            Template.from_string("[SLOT] d", slot_token="[SLOT]"), [us1, us2, ss5]
        )

        ts1 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"),
            [ss1, ss2, ss3, ss4],
        )
        ts2 = TemplateTree(
            Template.from_string("[SLOT] d", slot_token="[SLOT]"), [ts1, ss5]
        )

        collapsed_u = us3.collapse()
        self.assertEqual(ts2, collapsed_u)

    def test_equals(self):
        """ Tests the TemplateTree __eq__ """
        e1 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"),
            [self.s1, self.s2],
        )
        self.assertEqual(e1, self.u1)
        self.assertEqual(e1, e1)
        self.assertEqual(self.t3, self.t3)
        self.assertNotEqual(e1, self.u2)
        self.assertNotEqual(e1, self.t1)

    def test_equals_new_leaves(self):
        """ Test if Template Trees are equal if different leaves are used by constructing new trees from scratch"""

        s1 = TemplateTree(Template.from_string("a b c d"))
        s2 = TemplateTree(Template.from_string("a b e d"))
        s3 = TemplateTree(Template.from_string("a b f d"))
        s4 = TemplateTree(Template.from_string("g b h d"))
        u1 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"), [s1, s2]
        )
        u2 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"), [s3, u1]
        )
        u2_selfs3 = TemplateTree(
            Template.from_string("a b [SLOT] d", slot_token="[SLOT]"), [self.s3, u1]
        )
        u3 = TemplateTree(
            Template.from_string("[SLOT] b [SLOT] d", slot_token="[SLOT]"), [s4, u2]
        )

        self.assertEqual(self.s1, s1)
        self.assertEqual(self.s2, s2)
        self.assertEqual(self.s3, s3)
        self.assertEqual(self.s4, s4)
        self.assertEqual(self.u1, u1)
        self.assertEqual(self.u2, u2_selfs3)
        self.assertEqual(self.u2, u2)
        self.assertEqual(self.u3, u3)

    def test_get_descendent_leaves(self):
        """ Test if all leaves are properly found"""
        self.assertEqual({self.s1, self.s2}, set(self.u1.get_descendant_leaves()))
        self.assertEqual(
            {self.s1, self.s2, self.s3}, set(self.u2.get_descendant_leaves())
        )
        self.assertEqual(
            {self.s1, self.s2, self.s3, self.s4}, set(self.u3.get_descendant_leaves())
        )
        self.assertEqual(set(self.all_s), set(self.u4.get_descendant_leaves()))

        self.assertEqual(
            {self.s1, self.s2, self.s3}, set(self.t1.get_descendant_leaves())
        )
        self.assertEqual(
            {self.s1, self.s2, self.s3, self.s4}, set(self.t2.get_descendant_leaves())
        )
        self.assertEqual(set(self.all_s), set(self.t3.get_descendant_leaves()))

    def test_get_slot_content(self):
        self.assertEqual(
            {(Template.from_string("c"),), (Template.from_string("e"),)},
            self.u1.get_slot_contents_tuples(),
        )
        self.assertEqual(
            {(Template.from_string("[SLOT]"),), (Template.from_string("f"),)},
            self.u2.get_slot_contents_tuples(),
        )
        self.assertEqual(
            {
                (Template.from_string("c"),),
                (Template.from_string("e"),),
                (Template.from_string("f"),),
            },
            self.t1.get_slot_contents_tuples(),
        )

    def test_get_descendent_leaves_slot_content(self):
        # Same tests as before without recursion
        self.assertEqual(
            {(Template.from_string("c"),), (Template.from_string("e"),)},
            self.u1.get_descendent_leaves_slot_content_tuples(),
        )
        self.assertEqual(
            {
                (Template.from_string("c"),),
                (Template.from_string("e"),),
                (Template.from_string("f"),),
            },
            self.t1.get_descendent_leaves_slot_content_tuples(),
        )

        # New tests
        self.assertEqual(
            {
                (Template.from_string("c"),),
                (Template.from_string("e"),),
                (Template.from_string("f"),),
            },
            self.u2.get_descendent_leaves_slot_content_tuples(),
        )

    def test_get_slot_content_mappings(self):
        self.assertEqual(set(), self.s1.get_slot_content_mappings())

        slot1 = NamedTemplateSlot("x")
        slot2 = NamedTemplateSlot("y")
        a = TemplateString("a")
        b = TemplateString("b")
        c = TemplateString("c")

        # Simple tree
        simple_tree = TemplateTree(
            Template([a, slot1]), [TemplateTree(Template([a, b]), [])]
        )
        simple_slot_contents = simple_tree.get_slot_content_mappings()

        self.assertEqual(1, len(simple_slot_contents))
        simple_slot_content = list(simple_slot_contents)[0]
        self.assertTrue(slot1 in simple_slot_content)
        self.assertTrue(slot1 in simple_slot_content.keys())
        self.assertEqual(Template([b]), simple_slot_content[slot1])

        self.assertEqual({SlotAssignment({slot1: Template([b])})}, simple_slot_contents)

        # Two slot tree
        two_slot_tree = TemplateTree(
            Template([slot1, b, slot2]), [TemplateTree(Template([a, b, c]), [])]
        )
        two_slot_tree_contents = two_slot_tree.get_slot_content_mappings()
        self.assertEqual(
            {SlotAssignment({slot1: Template([a]), slot2: Template([c])})},
            two_slot_tree_contents,
        )

        # Test tree
        u1_slot = self.u1.get_template().get_slots()[0]
        self.assertEqual(
            {
                SlotAssignment({u1_slot: Template([TemplateString("c")])}),
                SlotAssignment({u1_slot: Template([TemplateString("e")])}),
            },
            self.u1.get_slot_content_mappings(),
        )

    def test_get_all_descendent_slots_breadth_first(self):
        self.assertEqual(1, len(self.u1.get_all_descendent_slots_breadth_first()))
        self.assertEqual(2, len(self.u2.get_all_descendent_slots_breadth_first()))
        self.assertEqual(4, len(self.u3.get_all_descendent_slots_breadth_first()))
        self.assertEqual(5, len(self.u4.get_all_descendent_slots_breadth_first()))
        self.assertEqual(4, len(self.t3.get_all_descendent_slots_breadth_first()))

    def test_collapse_using_slot_values(self):
        hello = TemplateString("hello")
        hey = TemplateString("hey")
        world = TemplateString("world")
        universe = TemplateString("universe")

        h1 = TemplateTree(Template([hello, world]))
        h2 = TemplateTree(Template([hey, world]))
        h3 = TemplateTree(Template([hello, universe]))
        h4 = TemplateTree(Template([hey, universe]))

        slot_a = NamedTemplateSlot("A")
        slot_b = NamedTemplateSlot("B")
        slot_c = NamedTemplateSlot("C")

        expected = TemplateTree(Template([slot_a, slot_b]), [h1, h2, h3, h4])
        expected_values = SlotValues(
            {
                slot_a: {Template([hello]), Template([hey])},
                slot_b: {Template([world]), Template([universe])},
            }
        )

        # Test first argument
        hello_t = Template([hello, slot_b])
        hello_tt = TemplateTree(hello_t, [h1, h3])
        hey_t = Template([hey, slot_b])
        hey_tt = TemplateTree(hey_t, [h2, h4])
        greeting_t = Template([slot_a, slot_b])
        greeting_tt = TemplateTree(greeting_t, [hello_tt, hey_tt])

        self.assertTrue(greeting_t.encompasses(hey_t, expected_values))
        self.assertTrue(greeting_t.encompasses(hello_t, expected_values))
        self.assertFalse(hello_t.encompasses(greeting_t, expected_values))

        self.assertEqual(
            expected_values, greeting_tt.calculated_merged_independent_slot_values()
        )

        self.assertEqual(
            expected, greeting_tt.collapse_using_slot_values(expected_values)
        )

        # Do same, but for second argument
        world_t = Template([slot_a, world])
        world_tt = TemplateTree(world_t, [h1, h2])
        universe_t = Template([slot_a, universe])
        universe_tt = TemplateTree(universe_t, [h3, h4])
        place_t = Template([slot_a, slot_b])
        place_tt = TemplateTree(place_t, [world_tt, universe_tt])

        self.assertEqual(
            expected_values, place_tt.calculated_merged_independent_slot_values()
        )

        self.assertEqual(expected, place_tt.collapse_using_slot_values(expected_values))

        # Test mix
        mix_tt = TemplateTree(place_t, [world_tt, hey_tt, h3])

        self.assertEqual(
            expected_values, mix_tt.calculated_merged_independent_slot_values()
        )

        self.assertEqual(expected, mix_tt.collapse_using_slot_values(expected_values))

        # Now with some noise
        noise = Template([TemplateString("noise")])
        noise_tt = TemplateTree(noise)

        noise_t = Template([slot_c])
        full_noise_tt = TemplateTree(noise_t, [greeting_tt, noise_tt])

        noise_values = SlotValues(
            {
                slot_a: {Template([hello]), Template([hey])},
                slot_b: {Template([world]), Template([universe])},
                slot_c: {Template([slot_a, slot_b]), noise},
            }
        )

        collapsed_full_noise = full_noise_tt.collapse_using_slot_values(noise_values)

        self.assertEqual(
            noise_values, full_noise_tt.calculated_merged_independent_slot_values(),
        )
        self.assertEqual(
            TemplateTree(Template([slot_c]), [expected, noise_tt]),
            collapsed_full_noise,
        )

    def test_collapse_using_slot_values(self):
        hello = TemplateString("hello")
        hey = TemplateString("hey")
        hi = TemplateString("hi")

        h1 = TemplateTree(Template([hello, hello]))
        h2 = TemplateTree(Template([hey, hello]))
        h3 = TemplateTree(Template([hello, hi]))
        h4 = TemplateTree(Template([hi, hello]))
        h5 = TemplateTree(Template([hi, hi]))

        hello_t = Template([hello])
        hey_t = Template([hey])
        hi_t = Template([hi])

        slot_a = NamedTemplateSlot("A")
        slot_b = NamedTemplateSlot("B")
        slot_c = NamedTemplateSlot("C")
        slot_d = NamedTemplateSlot("D")
        slot_e = NamedTemplateSlot("E")
        slot_f = NamedTemplateSlot("F")

        t1 = TemplateTree(Template([hello, slot_a]), [h1, h3])
        t2 = TemplateTree(Template([slot_b, hello]), [h1, h2, h4])
        t3 = TemplateTree(Template([slot_c, hi]), [h3, h5])
        t4 = TemplateTree(Template([hi, slot_d]), [h4, h5])
        t5 = TemplateTree(Template([slot_e, slot_f]), [t1, t2, t3, t4])

        slot_values = SlotValues(
            {
                slot_a: {Template([slot_e])},
                slot_b: {Template([slot_e])},
                slot_c: {Template([slot_e])},
                slot_d: {Template([slot_e])},
                slot_e: {hello_t, hi_t, hey_t},
                slot_f: {Template([slot_e])},
            }
        )

        self.assertEqual(
            slot_values,
            t5.get_slot_values().merge_slots(relative_similarity_threshold=0.01),
        )
        renamed_tree = t5.name_template_slots(
            {
                slot_a: slot_e,
                slot_b: slot_e,
                slot_c: slot_e,
                slot_d: slot_e,
                slot_f: slot_e,
            }
        )
        collapsed_tree = renamed_tree.collapse_using_slot_values(slot_values)
        self.assertEqual(Template([slot_e, slot_e]), collapsed_tree.get_template())
        self.assertEqual(
            {tt.get_template() for tt in [h1, h2, h3, h4, h5]},
            {tt.get_template() for tt in collapsed_tree.get_children()},
        )


if __name__ == "__main__":
    unittest.main()
