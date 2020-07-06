import random
import re
import unittest
from pathlib import Path

from src.context_free_grammar import ContextFreeGrammar, SlotReplacements, _tracery_slot_modifier
from src.template import Template
from src.template_elements import NamedTemplateSlot, TemplateString


class ContextFreeGrammarTest(unittest.TestCase):
    def setUp(self):
        random.seed(123)
        self.simple = ContextFreeGrammar.from_string(
            {"origin": ["expands only to one texts"]}
        )
        self.hello_world = ContextFreeGrammar.from_string(
            {
                "origin": ["<hello> <world>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )

        self.hello_world_single_a = ContextFreeGrammar.from_string(
            {"origin": ["<hello> <world>"], "hello": ["hello"], "world": ["world"]}
        )
        self.hello_world_single_b = ContextFreeGrammar.from_string(
            {"origin": ["<a> <b>"], "a": ["hello"], "b": ["world"]}
        )

    def test_from_string(self):
        input_dict = {"A": ["<B>, world", "hi"], "B": ["hello"]}
        expected_output = ContextFreeGrammar(
            {
                NamedTemplateSlot("A"): [
                    Template(
                        [
                            NamedTemplateSlot("B"),
                            TemplateString(","),
                            TemplateString("world"),
                        ]
                    ),
                    Template([TemplateString("hi")]),
                ],
                NamedTemplateSlot("B"): [Template([TemplateString("hello")])],
            }
        )
        output = ContextFreeGrammar.from_string(input_dict)
        self.assertEqual(expected_output, output)

    def test_get_depth(self):
        self.assertEqual(1, self.simple.get_depth())
        self.assertEqual(2, self.hello_world.get_depth())
        self.assertEqual(2, self.hello_world_single_a.get_depth())
        self.assertEqual(2, self.hello_world_single_b.get_depth())
        self.assertEqual(
            4,
            ContextFreeGrammar.from_string(
                {"origin": ["<A>"], "A": ["<B>"], "B": ["<C>"], "C": ["hi"],}
            ).get_depth(),
        )

    def test_generate_flat(self):
        hello_world_single = ContextFreeGrammar.from_string(
            {"origin": ["<hello> <world>"], "hello": ["hello"], "world": ["world"],}
        )
        self.assertEqual("hello world", hello_world_single.generate().to_flat_string())

    def test_generate_more(self):
        hello_world_possibilities = {
            self.hello_world.generate().to_flat_string() for _ in range(50)
        }
        self.assertEqual(
            {
                "hello world",
                "hi world",
                "hey world",
                "hello universe",
                "hi universe",
                "hey universe",
            },
            hello_world_possibilities,
        )

    def test_generate_same_name(self):
        hello_world_single = ContextFreeGrammar.from_string(
            {"origin": ["I like <X> and <X>"], "X": ["cats", "dogs", "pandas"],}
        )
        possibilities = {
            "I like cats and cats",
            "I like cats and dogs",
            "I like cats and pandas",
            "I like dogs and cats",
            "I like dogs and dogs",
            "I like dogs and pandas",
            "I like pandas and cats",
            "I like pandas and dogs",
            "I like pandas and pandas",
        }
        for i in range(100):
            self.assertTrue(
                hello_world_single.generate().to_flat_string() in possibilities
            )
        self.assertEqual(
            possibilities,
            {g.to_flat_string() for g in hello_world_single.generate_all()},
        )

    def test_generate_all(self):
        hello_world_possibilities = set(
            t.to_flat_string() for t in self.hello_world.generate_all()
        )
        self.assertEqual(
            {
                "hello world",
                "hi world",
                "hey world",
                "hello universe",
                "hi universe",
                "hey universe",
            },
            hello_world_possibilities,
        )

    def test_get_possible_isomorphic_nt_replacements(self):
        self.assertEqual(
            {
                SlotReplacements(
                    {NamedTemplateSlot("origin"): NamedTemplateSlot("origin")}
                )
            },
            set(self.simple.get_isomorphic_replacements(self.simple)),
        )
        self.assertEqual(
            {
                SlotReplacements(
                    {
                        NamedTemplateSlot("origin"): NamedTemplateSlot("origin"),
                        NamedTemplateSlot("hello"): NamedTemplateSlot("a"),
                        NamedTemplateSlot("world"): NamedTemplateSlot("b"),
                    }
                )
            },
            set(
                self.hello_world_single_a.get_isomorphic_replacements(
                    self.hello_world_single_b
                )
            ),
        )

    def test_isomorphic_simple(self):
        self.assertTrue(self.simple.is_isomorphic_with(self.simple))
        self.assertTrue(
            self.hello_world_single_a.is_isomorphic_with(self.hello_world_single_b)
        )
        self.assertTrue(
            self.hello_world_single_a.is_isomorphic_with(self.hello_world_single_b)
        )
        self.assertFalse(self.hello_world_single_a.is_isomorphic_with(self.hello_world))

    def check_isomorphism(self, *grams):
        self.assertGreater(len(grams), 0)
        for gram1 in grams:
            for gram2 in grams:
                self.assertTrue(gram1.is_isomorphic_with(gram2))

    def test_isomorphic_nested(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                "origin": ["<a> <world>"],
                "a": ["<hello>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )
        gram2 = ContextFreeGrammar.from_string(
            {
                "origin": ["<b> <w>"],
                "b": ["<c>"],
                "c": ["hello", "hi", "hey"],
                "w": ["world", "universe"],
            }
        )

        # Test with self
        self.check_isomorphism(gram1, gram2)

        self.assertFalse(gram1.is_isomorphic_with(self.hello_world_single_a))

    def test_not_isomorphic_same_keys(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                "origin": ["<a> <world>"],
                "a": ["<hello>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )
        gram2 = ContextFreeGrammar.from_string(
            {
                "origin": ["<a> <world>"],
                "a": ["<hello>"],
                "hello": ["a", "b", "c"],
                "world": ["d", "e"],
            }
        )
        self.assertFalse(gram1.is_isomorphic_with(gram2))
        self.assertFalse(gram2.is_isomorphic_with(gram1))

    def test_isomorphic_multiple_possibilities_simple(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                "origin": ["<a> world", "<b> world"],
                "a": ["<hello>"],
                "b": ["<world>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )
        gram2 = ContextFreeGrammar.from_string(
            {
                "origin": ["<1> world", "<2> world"],
                "1": ["<h>"],
                "2": ["<w>"],
                "h": ["hello", "hi", "hey"],
                "w": ["world", "universe"],
            }
        )
        gram3 = ContextFreeGrammar.from_string(
            {
                "origin": ["<1> world", "<2> world"],
                "1": ["<w>"],
                "2": ["<h>"],
                "w": ["world", "universe"],
                "h": ["hello", "hi", "hey"],
            }
        )
        # Test with self
        self.check_isomorphism(gram1, gram2, gram3)

        # Test not isomorphic with others
        self.assertFalse(gram1.is_isomorphic_with(self.hello_world))
        self.assertFalse(gram2.is_isomorphic_with(self.hello_world))
        self.assertFalse(gram3.is_isomorphic_with(self.hello_world))

    def test_isomorphic_multiple_nt_refs(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                "origin": ["<a> world", "<c> world", "<b> <world>"],
                "a": ["<hello>"],
                "c": ["<hello>"],
                "b": ["<world>", "<hello>"],
                "hello": ["hello", "hi", "hey", "<world>"],
                "world": ["world", "universe"],
            }
        )
        gram2 = ContextFreeGrammar.from_string(
            {
                "origin": ["<1> world", "<3> world", "<2> <w>"],
                "3": ["<h>"],
                "1": ["<h>"],
                "2": ["<w>", "<h>"],
                "h": ["hello", "hi", "hey", "<w>"],
                "w": ["world", "universe"],
            }
        )
        conflicting_gram = ContextFreeGrammar.from_string(
            {
                "origin": ["<1> world", "<1> world", "<2> <w>"],
                "1": ["<h>"],
                "2": ["<w>", "<h>"],
                "h": ["hello", "hi", "hey", "<w>"],
                "w": ["world", "universe"],
            }
        )
        # Test with self
        self.assertTrue(gram1.is_isomorphic_with(gram1))
        self.check_isomorphism(gram1, gram2)

        # Test not isomorphic with others
        self.assertFalse(gram1.is_isomorphic_with(conflicting_gram))
        self.assertFalse(gram2.is_isomorphic_with(conflicting_gram))
        self.assertFalse(gram1.is_isomorphic_with(self.hello_world))
        self.assertFalse(gram2.is_isomorphic_with(self.hello_world))

    def test_isomorphic_repeat(self):
        gram1 = ContextFreeGrammar.from_string(
            {"origin": ["<a>", "<a>", "<b>"], "a": ["<b>"], "b": ["world"],}
        )
        self.assertTrue(gram1.is_isomorphic_with(gram1))

    def test_isomorphic_recursive(self):
        gram1 = ContextFreeGrammar.from_string(
            {"origin": ["<a>", "a <origin>"], "a": ["world"],}
        )
        gram2 = ContextFreeGrammar.from_string(
            {"origin": ["<b>", "a <origin>"], "b": ["world"],}
        )
        conflicting_gram1 = ContextFreeGrammar.from_string(
            {"origin": ["<b>", "a <origin>"], "b": ["earth"],}
        )
        conflicting_gram2 = ContextFreeGrammar.from_string(
            {"origin": ["<b>", "b <origin>"], "b": ["world"],}
        )
        self.check_isomorphism(gram1, gram2)
        self.assertFalse(gram1.is_isomorphic_with(conflicting_gram1))
        self.assertFalse(gram1.is_isomorphic_with(conflicting_gram2))

    def test_isomorphic_advanced_self(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                # "origin": ["<a>",  "<b>", "<c>", "<d>", "<e>", "<f>", "<g>"],
                "origin": ["<a>", "<b>", "<c>", "<d>", "<e>"],
                "a": ["<hello>"],
                "b": ["<world>"],
                "c": ["<world>"],
                "d": ["<hello>", "<world>"],
                "e": ["<hello> <world>", "<hello>"],
                "f": ["<a>", "<hello>"],
                "g": ["<a>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )
        self.assertTrue(gram1.is_isomorphic_with(gram1))

    def test_isomorphic_advanced(self):
        gram1 = ContextFreeGrammar.from_string(
            {
                # "origin": ["<a>", "<b>", "<c>", "<d>", "<e>", "<f>", "<g>"],
                "origin": ["<a>", "<b>", "<c>", "<d>", "<e>"],
                "a": ["<hello>"],
                "b": ["<world>"],
                "c": ["<world>"],
                "d": ["<world>", "<hello>"],
                "e": ["<hello> <world>", "<hello>"],
                "f": ["<a>", "<hello>"],
                "g": ["<a>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe"],
            }
        )
        gram2 = ContextFreeGrammar.from_string(
            {
                # "origin": ["<1>", "<2>", "<3>", "<4>", "<5>", "<6>", "<7>"],
                "origin": ["<1>", "<2>", "<3>", "<4>", "<5>"],
                "1": ["<h>"],
                "2": ["<w>"],
                "3": ["<w>"],
                "4": ["<w>", "<h>"],
                "5": ["<h> <w>", "<h>"],
                "6": ["<1>", "<h>"],
                "7": ["<1>"],
                "h": ["hello", "hi", "hey"],
                "w": ["world", "universe"],
            }
        )
        # Test with self
        self.assertTrue(gram1.is_isomorphic_with(gram1))
        self.assertTrue(gram2.is_isomorphic_with(gram2))

        # Test with other
        self.assertTrue(gram1.is_isomorphic_with(gram2))
        self.assertTrue(gram2.is_isomorphic_with(gram1))

        # Check non isomorphic
        self.assertFalse(gram1.is_isomorphic_with(self.hello_world))
        self.assertFalse(gram2.is_isomorphic_with(self.hello_world))


    def test_modifier_removal_small(self):
        print(re.match(_tracery_slot_modifier, "#a.a#"))
        self.assertEqual("#a#", ContextFreeGrammar.replace_modifier_variables("#a.bla#"))
        self.assertEqual("#a#", ContextFreeGrammar.replace_modifier_variables("#a.title#"))
        self.assertEqual("#b#", ContextFreeGrammar.replace_modifier_variables("#b.title#"))
        self.assertEqual("#blabla#", ContextFreeGrammar.replace_modifier_variables("#blabla.title#"))

def get_tracery_folder() -> Path:
    return Path(__file__).parent / ".." / ".." / "data" / "raw" / "tracery"


if __name__ == "__main__":
    unittest.main()
