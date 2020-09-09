import random
import unittest
from typing import Collection

from gitta import template_tree_visualiser
from gitta.context_free_grammar import ContextFreeGrammar
from gitta.template import Template
from gitta.template_tree import TemplateTree
from gitta.template_tree_learner import (
    TemplateLatticeLearner,
    TemplateTreeLearner,
    LearnerState,
    _to_templates,
)
from gitta.template_tree_visualiser import render_tree_string


class TemplateTreeLearnerTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(123)
        self.hello_world_small = ContextFreeGrammar.from_string(
            {
                "origin": ["<hello> <world>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe", "earth"],
            }
        )
        self.hello_world_and_world_adjective = ContextFreeGrammar.from_string(
            {
                "origin": ["<hello>, <location>!", "The <location> is <adjective>"],
                "hello": ["Hello", "Greetings", "Howdy", "Hey"],
                "location": ["universe", "earth", "world", "solar system"],
                "adjective": ["pretty", "cool", "amazing"],
            }
        )

    def check_same_tree_learned(
        self, learner: TemplateTreeLearner, dataset: Collection[str], trials: int = 20
    ):
        first_tree = learner.learn(dataset)
        # print(template_tree_visualiser.render_tree_string(first_tree))
        for i in range(trials):
            random.shuffle(dataset)
            other_tree = learner.learn(dataset)
            self.assertEqual(
                first_tree,
                other_tree,
                "Non-equal trees "
                + str(i)
                + ":\n"
                + render_tree_string(first_tree)
                + "\n"
                + render_tree_string(other_tree),
            )

    def test_2_line_learner(self):
        learner = TemplateLatticeLearner(minimal_variables=True)
        dataset = ["hello world", "hi world"]
        template_tree = learner.learn(dataset)

        expected_top_template = Template.from_string("[SLOT] world")
        expected = TemplateTree(
            expected_top_template,
            [TemplateTree(Template.from_string(s)) for s in dataset],
        )
        print(template_tree_visualiser.render_tree_string(template_tree))
        self.assertEqual(expected_top_template, template_tree.get_template())
        self.assertEqual(expected, template_tree)

    def test_3_line_learner(self):
        learner = TemplateLatticeLearner(minimal_variables=True)
        dataset = ["hello world", "hi world", "hello universe"]
        template_tree = learner.learn(dataset)

        expected = TemplateTree(
            Template.from_string("[SLOT]"),
            [
                TemplateTree(
                    Template.from_string("[SLOT] world"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hi world"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("hello [SLOT]"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hello universe"]
                    ],
                ),
            ],
        )
        print(template_tree_visualiser.render_tree_string(template_tree))
        self.assertEqual(expected, template_tree)

    def test_4_line_learner(self):
        learner = TemplateLatticeLearner(minimal_variables=True)
        dataset = ["hello world", "hi world", "hello universe", "hi universe"]
        template_tree = learner.learn(dataset)

        expected = TemplateTree(
            Template.from_string("[SLOT]"),
            [
                TemplateTree(
                    Template.from_string("[SLOT] world"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hi world"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("[SLOT] universe"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello universe", "hi universe"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("hello [SLOT]"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hello universe"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("hi [SLOT]"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hi world", "hi universe"]
                    ],
                ),
            ],
        )
        print(template_tree_visualiser.render_tree_string(template_tree))
        self.assertEqual(expected, template_tree)

    def test_4_lines_initial_pairs(self):

        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        dataset = ["hello world", "hi world", "hello solar system", "hi solar system"]
        learner_state = LearnerState(_to_templates(dataset))
        initial_pairs = learner._create_initial_merge_candidates(
            learner_state.get_active_templates()
        )
        print(len(initial_pairs))
        for initial_pair in initial_pairs:
            print(initial_pair, "-->", initial_pair.get_merged_template())

    def test_4_line_learner_longer_second_initial_pairs_always_same(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        dataset = ["hello world", "hi world", "hello solar system", "hi solar system"]

        def get_initial_pairs():
            random.shuffle(dataset)
            learner_state = LearnerState(_to_templates(dataset))
            initial_pairs = learner._create_initial_merge_candidates(
                learner_state.get_active_templates()
            )
            return {p for p in initial_pairs if p.get_distance() <= 2}

        first_pairs = get_initial_pairs()
        for i in range(100):
            other_pairs = get_initial_pairs()
            self.assertEqual(len(first_pairs), len(other_pairs))

    def test_4_line_learner_longer_second(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        dataset = ["hello world", "hi world", "hello solar system", "hi solar system"]
        template_tree = learner.learn(dataset)

        expected = TemplateTree(
            Template.from_string("[SLOT]"),
            [
                TemplateTree(
                    Template.from_string("[SLOT] world"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hi world"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("[SLOT] solar system"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello solar system", "hi solar system"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("hello [SLOT]"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hello world", "hello solar system"]
                    ],
                ),
                TemplateTree(
                    Template.from_string("hi [SLOT]"),
                    [
                        TemplateTree(Template.from_string(s))
                        for s in ["hi world", "hi solar system"]
                    ],
                ),
            ],
        )
        print(template_tree_visualiser.render_tree_string(template_tree))
        self.assertEqual(expected, template_tree)

    def test_learn_hello_world_tree(self):
        learner = TemplateLatticeLearner(minimal_variables=True)
        dataset = list(self.hello_world_small.generate_all_string())
        template_tree = learner.learn(dataset)
        print(template_tree_visualiser.render_tree_string(template_tree.collapse()))

    def test_learn_hello_world_tree_larger(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        dataset = list(self.hello_world_and_world_adjective.generate_all_string())
        template_tree = learner.learn(dataset)
        print(template_tree_visualiser.render_tree_string(template_tree))

        pruned_template_tree = template_tree.prune_redundant_abstractions()
        print(
            "pruned\n",
            template_tree_visualiser.render_tree_string(pruned_template_tree),
        )

        # Only two templates in the top
        top_templates = {
            tt.get_template() for tt in pruned_template_tree.get_children()
        }
        self.assertEqual(
            {
                Template.from_string("The [SLOT] is [SLOT]"),
                Template.from_string("[SLOT], [SLOT]!"),
            },
            top_templates,
        )
        self.assertEqual(
            set(dataset),
            set(
                {
                    t.get_template().to_flat_string()
                    for t in pruned_template_tree.get_descendant_leaves()
                }
            ),
        )

    def test_same_tree_induction_small(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=1)
        dataset = list(self.hello_world_small.generate_all_string())
        self.check_same_tree_learned(learner, dataset)

    # TODO: Fix
    # def test_same_tree_induction_larger(self):
    #     learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
    #     dataset = list(self.hello_world_and_world_adjective.generate_all_string())
    #     self.check_same_tree_learned(learner, dataset)

    def test_get_best_merge_candidate(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        template_1 = Template.from_string("The solar system is [SLOT]")
        template_1_point = Template.from_string("The solar system is [SLOT].")
        template_2 = Template.from_string("[SLOT], solar system!")

        template_3 = Template.from_string("The earth is [SLOT]")
        template_3_point = Template.from_string("The earth is [SLOT].")

        merge_1_2 = learner._get_best_merge_candidate(template_1, template_2)
        self.assertEqual(
            Template.from_string("[SLOT] solar system [SLOT]"),
            merge_1_2.get_merged_template(minimal_variables=True),
        )
        self.assertEqual(
            3, merge_1_2.get_distance(),
        )

        merge_1_3 = learner._get_best_merge_candidate(template_1, template_3)
        self.assertEqual(
            Template.from_string("The [SLOT] is [SLOT]"),
            merge_1_3.get_merged_template(minimal_variables=True),
        )
        self.assertEqual(
            3, merge_1_3.get_distance(),
        )

        # With punctuation version
        merge_1_2p = learner._get_best_merge_candidate(template_1_point, template_2)
        self.assertEqual(
            Template.from_string("[SLOT] solar system [SLOT]"),
            merge_1_2p.get_merged_template(minimal_variables=True),
        )
        self.assertEqual(
            4, merge_1_2p.get_distance(),
        )

        merge_1_3p = learner._get_best_merge_candidate(
            template_1_point, template_3_point
        )
        self.assertEqual(
            Template.from_string("The [SLOT] is [SLOT]."),
            merge_1_3p.get_merged_template(minimal_variables=True),
        )
        self.assertEqual(
            3, merge_1_3p.get_distance(),
        )

    def test_get_best_merge_candidate_hello_world(self):
        learner = TemplateLatticeLearner(minimal_variables=True, words_per_leaf_slot=2)
        template_1 = Template.from_string("hello world")
        template_2 = Template.from_string("hi solar system")

        merge_1_2 = learner._get_best_merge_candidate(template_1, template_2)
        self.assertEqual(
            Template.from_string("[SLOT]"),
            merge_1_2.get_merged_template(minimal_variables=True),
        )
        self.assertEqual(
            4, merge_1_2.get_distance(),
        )


if __name__ == "__main__":
    unittest.main()
