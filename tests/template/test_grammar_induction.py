import random
import unittest
from typing import List, Collection


from src import grammar_induction
from src.context_free_grammar import ContextFreeGrammar
from src.template import Template

import random
from pathlib import Path


class GrammarLearning(unittest.TestCase):
    def setUp(self):
        random.seed(42)
        self.hello_world_small = ContextFreeGrammar.from_string(
            {
                "origin": ["<hello> <world>"],
                "hello": ["hello", "hi", "hey"],
                "world": ["world", "universe", "earth"],
            }
        )
        self.hello_world_full = ContextFreeGrammar.from_string(
            {
                "origin": "<hello>, <location>!",
                "hello": ["Hello", "Greetings", "Howdy", "Hey"],
                "location": ["world", "solar system", "galaxy", "universe"],
            }
        )

    def check_grammar_induction_correctness(
        self,
        expected_grammar: ContextFreeGrammar,
        dataset: List[str] = None,
        words_per_slot=1,
        prune_redundant=True,
        minimal_variables=True,
    ) -> ContextFreeGrammar:
        if dataset is None:
            dataset = expected_grammar.generate_all_string()
        induced_grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset,
            words_per_slot=words_per_slot,
            prune_redundant=prune_redundant,
            minimal_variables=minimal_variables,
        )

        print(induced_grammar)
        # Check if same dataset generation
        self.check_grammar_expansion(induced_grammar, dataset)

        # Check if isomorph grammar
        self.assertTrue(expected_grammar.is_isomorphic_with(induced_grammar))

        # Check that the grammar is representable as string, without exception
        self.assertTrue(len(str(induced_grammar)) > 0)

        return induced_grammar

    def check_grammar_expansion(
        self, grammar: ContextFreeGrammar, expected_expansion: Collection[str]
    ):
        """ Check that grammar indeed generates the dataset it learned from """
        generated_dataset = grammar.generate_all_string()
        self.assertEqual(set(expected_expansion), set(generated_dataset))

    # Normal case
    def test_small_grammar_induction(self):
        dataset = list(self.hello_world_small.generate_all_string())
        grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset, words_per_slot=1, minimal_variables=False
        )
        print(grammar)

        # Check if grammar generates same dataset
        self.check_grammar_expansion(grammar, dataset)

        # Check that size of the grammar is smaller than dataset
        self.assertTrue(grammar.get_size() < len(dataset))

        # Check that same grammar
        self.assertTrue(grammar.is_isomorphic_with(self.hello_world_small))

    def test_hello_world_full_grammar_induction(self):
        # Check if grammar generates same dataset
        grammar = self.check_grammar_induction_correctness(
            self.hello_world_full, words_per_slot=2
        )
        print(grammar)

    def test_hello_world_multiple_origin_options(self):
        # Check if grammar generates same dataset
        grammar = self.check_grammar_induction_correctness(
            ContextFreeGrammar.from_string(
                {
                    "origin": ["<hello>, <location>!", "The <location> is <adjective>"],
                    "hello": ["Hello", "Greetings", "Howdy", "Hey"],
                    "location": ["world", "universe", "earth"],
                    "adjective": ["pretty", "cool", "awesome"],
                }
            ),
            words_per_slot=1,
        )
        print(grammar)

    def test_hello_world_multiple_origin_options_multiple_words(self):
        # Check if grammar generates same dataset
        grammar = self.check_grammar_induction_correctness(
            ContextFreeGrammar.from_string(
                {
                    "origin": ["<hello>, <location>!", "The <location> is <adjective>"],
                    "hello": ["Hello", "Greetings", "Howdy", "Hey"],
                    "location": ["world", "solar system"],
                    "adjective": ["pretty", "cool"],
                }
            ),
            words_per_slot=2,
        )
        print(grammar)

    # def test_recursive(self):
    #     grammar = ContextFreeGrammar.from_string(
    #         {
    #             "origin": [" <L> <R> ", " <L> <R> <L> <R> ", " <L> <L> <R> <R> "],
    #             "L": [" ( <origin>", "<origin> )", "(", "(", "(", "(", "(", "(", "(", "("],
    #             "R": ["<origin> )", " ) <origin>", ")", ")", ")", ")", ")", ")", ")", ")"],
    #         }
    #     )
    #     dataset = [grammar.generate().to_flat_string() for i in range(20)]
    #
    #     induced_grammar = grammar_induction.induce_grammar_using_template_trees(
    #         dataset,
    #         words_per_slot=1,
    #     )
    #     print(induced_grammar)

    # TODO: fix test
    # def test_hello_world_similar_prefix(self):
    #     # Check if grammar generates same dataset
    #     grammar = self.check_grammar_induction_correctness(
    #         ContextFreeGrammar.from_string(
    #             {
    #                 "origin": ["<hello> <location>!", "<hello> there, <person>!"],
    #                 "hello": ["Hello", "Greetings"],
    #                 "location": ["world", "earth",],
    #                 "person": ["Ann", "Bob", "Chloe"],
    #             }
    #         ),
    #         words_per_slot=1,
    #     )
    #     print(grammar)

    def test_no_recursion(self):
        grammar = ContextFreeGrammar.from_string(
            {
                "origin": ["<hello> <location>!", "<hello> there <hello> kid"],
                "hello": ["hello", "greetings"],
                "location": ["world", "earth"],
            }
        )
        dataset = [t.to_flat_string() for t in grammar.generate_all()]
        dataset.sort()
        induced_grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset,
            words_per_slot=1,
            prune_redundant=True,
            minimal_variables=True,
            max_recalculation=None,
        )
        print(induced_grammar)
        self.assertFalse(induced_grammar.is_recursive())

    def test_slot_repeat(self):
        grammar = self.check_grammar_induction_correctness(
            ContextFreeGrammar.from_string(
                {"origin": ["<a> <a>"], "a": ["1", "2", "3"],}
            ),
            words_per_slot=1,
            minimal_variables=True,
        )
        print(grammar)

    def test_repeat_2(self):
        grammar = ContextFreeGrammar.from_string(
            {
                "origin": [
                    "I really like <X> and <X>",
                    "<X> are not supposed to be in the zoo",
                ],
                "X": ["cats", "dogs", "geese", "bananas"],
            }
        )
        dataset = [t.to_flat_string() for t in grammar.generate_all()]
        dataset.sort()
        induced_grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset,
            words_per_slot=1,
            prune_redundant=True,
            minimal_variables=True,
            max_recalculation=None,
        )
        print(induced_grammar)
        self.assertTrue(grammar.is_isomorphic_with(induced_grammar))
        self.assertFalse(induced_grammar.is_recursive())

    def test_repeat_2_missing_data(self):
        grammar = ContextFreeGrammar.from_string(
            {
                "origin": [
                    "I like <X> and <X>",
                    "<X> are not supposed to be in the zoo",
                ],
                "X": ["cats", "dogs", "geese", "bananas"],
            }
        )
        dataset = [
            "I like cats and dogs",
            "I like bananas and geese",
            "I like geese and cats",
            "bananas are not supposed to be in the zoo",
            "geese are not supposed to be in the zoo",
        ]
        induced_grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset,
            words_per_slot=1,
            prune_redundant=True,
            minimal_variables=True,
            max_recalculation=None,
            relative_similarity_threshold=0.01,
        )
        print(induced_grammar)
        self.assertTrue(grammar.is_isomorphic_with(induced_grammar))
        self.assertFalse(induced_grammar.is_recursive())

    def test_hello_world_multiple_deep(self):
        # Check if grammar generates same dataset
        grammar = self.check_grammar_induction_correctness(
            ContextFreeGrammar.from_string(
                {
                    "origin": ["<a>, <b>!"],
                    "a": ["1", "2", "3"],
                    "b": ["4", "5", "6", "- <c>"],
                    "c": ["7", "8", "9"],
                }
            ),
            words_per_slot=2,
            minimal_variables=True,
        )
        print(grammar)
        self.assertFalse(grammar.is_recursive())

    # def test_hello_world_multiple_deep_no_separator(self):
    #     # Check if grammar generates same dataset
    #     grammar = self.check_grammar_induction_correctness(
    #         ContextFreeGrammar.from_string(
    #             {
    #                 "origin": ["<a> <b>"],
    #                 "a": ["1", "2", "3"],
    #                 "b": ["4", "5", "6", "- <c>"],
    #                 "c": ["7", "8", "9"],
    #             }
    #         ),
    #         words_per_slot=1,
    #     )
    #     print(grammar)

    # TODO: fix test
    # def test_hello_world_multiple_repeated_1(self):
    #     # Check if grammar generates same dataset
    #     grammar = self.check_grammar_induction_correctness(
    #         ContextFreeGrammar.from_string(
    #             {
    #                 "origin": ["<hello>, <location>!", "<hello> there, <person>!"],
    #                 "hello": ["Hello", "Greetings", "Howdy", "Hey"],
    #                 "location": ["world", "solar system", "galaxy", "universe",],
    #                 "person": ["Ann", "Bob", "Chloe"],
    #             }
    #         ),
    #         words_per_slot=2,
    #     )
    #     print(grammar)
    #
    # TODO: fix test
    # def test_hello_world_multiple_repeated_2(self):
    #     # Check if grammar generates same dataset
    #     grammar = self.check_grammar_induction_correctness(
    #         ContextFreeGrammar.from_string(
    #             {
    #                 "origin": ["<hello>, <location>!", "<person>: <hello> <location>"],
    #                 "hello": ["Hello", "Greetings", "Howdy", "Hey"],
    #                 "location": [
    #                     "world",
    #                     "solar system",
    #                     "galaxy",
    #                     "universe",
    #                     "there, <person>",
    #                 ],
    #                 "person": ["Ann", "Bob", "Chloe"],
    #             }
    #         )
    #     )
    #     print(grammar)

    # Test how it deals with noise
    def test_small_grammar_induction_noisy(self):
        dataset = list(self.hello_world_small.generate_all_string())
        dataset += ["noise"]

        grammar = grammar_induction.induce_grammar_using_template_trees(dataset)
        print(grammar)

        # Check if grammar generates same dataset
        self.check_grammar_expansion(grammar, dataset)

        # Check that size of the grammar is smaller than dataset
        self.assertTrue(grammar.get_size() < len(dataset))

    def test_hello_world_full_grammar_induction_noisy(self):
        dataset = list(self.hello_world_full.generate_all_string())
        dataset += ["noise"]

        grammar = grammar_induction.induce_grammar_using_template_trees(dataset)
        print(grammar)

        # Check if grammar generates same dataset
        self.check_grammar_expansion(grammar, dataset)

        # Check that size of the grammar is smaller than dataset
        self.assertTrue(grammar.get_size() < len(dataset))

    def test_small_grammar_induction_missing_data(self):
        full_dataset = set(self.hello_world_small.generate_all_string())
        dataset = set(full_dataset)
        # dataset.remove("hello world")
        dataset.remove("hi universe")
        # print("dataset", dataset)

        grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset, relative_similarity_threshold=0.1, minimal_variables=False
        )
        print(grammar)

        # Check if grammar generates same dataset
        self.check_grammar_expansion(grammar, full_dataset)

        # Check that size of the grammar is smaller than dataset
        self.assertTrue(grammar.get_size() < len(full_dataset))

    def test_reoccuring_slot(self):
        dataset = ["I like cats and dogs", "I like dogs and chickens"]
        grammar = grammar_induction.induce_grammar_using_template_trees(
            dataset, relative_similarity_threshold=0.1, minimal_variables=True
        )

        non_terminals = grammar.get_slots()
        self.assertEqual(2, len(non_terminals))
        word_list_nt = [s for s in non_terminals if s is not grammar.get_start()][0]

        # Assert only one top template
        origin_templates = grammar.get_content_for(grammar.get_start())
        self.assertEqual(1, len(origin_templates))

        # Check origin template
        origin_template: Template = origin_templates[0]
        self.assertTrue(
            Template.from_string("I like [SLOT] and [SLOT]").has_same_shape(
                origin_template
            )
        )

        # Check top template has only one named slot
        self.assertEqual(1, len(set(origin_template.get_slots())))

        # Check if slot has properly merged values
        self.assertEqual(
            {"cats", "dogs", "chickens"},
            {t.to_flat_string() for t in grammar.get_content_for(word_list_nt)},
        )

    def test_large_data(self):
        data_file_path = (
            Path(__file__).parent
            / ".."
            / ".."
            / "data"
            / "raw"
            / "scenes_from_a_hat.tsv"
        )
        dataset = []
        min_number_of_interactions = 15

        with open(data_file_path.resolve()) as data_file:
            i = 0
            for line in data_file.readlines():
                i += 1
                if not "meta" in line.lower():
                    if not "\t" in line or len(line.split("\t")) < 3:
                        print("Error line", i, line)
                    score, comments, text = line.split("\t")
                    if int(score) + int(comments) >= min_number_of_interactions:
                        dataset.append(text.strip())

        random.seed(42)
        random.shuffle(dataset)
        small_dataset = dataset[:30]
        grammar = grammar_induction.induce_grammar_using_template_trees(
            small_dataset,
            words_per_slot=3,
            prune_redundant=True,
            relative_similarity_threshold=0.05,
            minimal_variables=True,
        )
        print(grammar)
        print("Size", grammar.get_size())
        print("Recursive", grammar.is_recursive())

    def test_botdoesnot_crash(self):
        dataset = [
            "One does not easily lead into Qumar",
            "One does not candidly turn into Brobdingnag",
            "One does not frankly take a constitutional into Luftnarp",
            "One does not frankly troop into Cortuguay",
            "One does not intelligibly travel on foot into West Britannia",
            "One does not honestly troop into Sylvania",
            "One does not without any elaboration hit the road into Kraplakistan",
            "One does not openly gait into Novistrana",
            "One does not ordinarily stroll into San Theodoros",
            "One does not naturally toddle into Bacteria",
            "One does not artlessly tramp into Panau",
            "One does not openly foot into Ruritania",
            "One does not quietly gait into São Rico",
            "One does not simply prance into Wadiya",
            "One does not unpretentiously hoof it into Markovia",
            "One does not openly jaunt into Cordinia",
            "One does not candidly leg into Guilder",
            "One does not honestly meander into Edonia",
            "One does not sincerely slog into Turgistan",
            "One does not sincerely wend one's way into San Theodoros",
            "One does not simply stalk into Krakozhia",
            "One does not directly traipse into The Organization of North American Nations",
            "One does not quietly go on foot into Norgborg",
            "One does not naturally tread into The North American Confederacy",
            "One does not honestly airing into Sunda",
            "One does not simply rove into Ragaan",
            "One does not quietly run into The Organization of North American Nations",
            "One does not openly travel on foot into Bruzundanga",
            "One does not candidly traipse into Zekistan",
            "One does not artlessly lead into Meropis",
            "One does not candidly toddle into Bolumbia",
            "One does not guilelessly lead into Glubbdubdrib",
            "One does not ordinarily lumber into The National Republic of Umbutu (Republique Nationale d'Umbutu )",
            "One does not candidly ambulate into Costa Luna",
            "One does not straightforwardly trudge into Graustark",
            "One does not ingenuously go into The New German Republic",
            "One does not without any elaboration step into Axphain",
            "One does not modestly tour into Nuevo Rico",
            "One does not sincerely traverse into Antegria",
            "One does not sincerely leg into Vadeem",
            "One does not guilelessly troop into Chernarus",
            "One does not candidly pace into Urkesh",
            "One does not simply file into Calbia",
            "One does not easily run into Mendorra",
            "One does not intelligibly roam into Costa Luna",
            "One does not guilelessly tour into The United States of South Africa",
            "One does not quietly go on foot into Carjackistan",
            "One does not without any elaboration hike into Glovania",
            "One does not unpretentiously stalk into Grinlandia",
            "One does not honestly traverse into Zekistan",
            "One does not simply file into Samavia",
            "One does not directly patrol into Idris",
            "One does not unaffectedly race into Zekistan",
            "One does not commonly trudge into Chernarus",
            "One does not sincerely run into Zephyria",
            "One does not modestly march into Maltovia",
            "One does not easily canter into Transia",
            "One does not honestly locomote into Khemed",
            "One does not naturally jaunt into Blefuscu",
            "One does not straightforwardly ambulate into Nerdocrumbesia",
            "One does not frankly scuff into Naruba",
            "One does not modestly knock about into Kerplankistan",
            "One does not artlessly meander into Mordor",
            "One does not unpretentiously rove into Fe'ausi",
            "One does not intelligibly lumber into Loompa Land",
            "One does not easily prance into Tomainia",
            "One does not easily hit the road into Gérolstein",
            "One does not unpretentiously knock about into Pottsylvania",
            "One does not openly hike into Kunami",
            "One does not ingenuously parade into Patusan",
            "One does not ordinarily run into Centopia",
            "One does not straightforwardly wend one's way into Loompa Land",
            "One does not frankly parade into Kinakuta",
            "One does not ordinarily ramble into Nerdocrumbesia",
            "One does not artlessly ambulate into The Kingdom of New Orleans",
            "One does not modestly lead into Kazirstan",
            "One does not quietly tread into Vadeem",
            "One does not quietly race into The Chinese Federation",
            "One does not modestly traverse into Glovania",
            "One does not simply troop into Aslerfan",
            "One does not ordinarily plod into Samavia",
            "One does not matter-of-factly trudge into Graznavia",
            "One does not matter-of-factly go into Arendelle",
            "One does not frankly run into Naruba",
            "One does not candidly trek into Transia",
            "One does not unaffectedly trudge into The United Islamic Republic",
            "One does not intelligibly wend one's way into Calbia",
            "One does not artlessly trek into The New California Republic",
            "One does not unaffectedly travel on foot into Florin",
            "One does not intelligibly step into Gondal",
            "One does not naturally locomote into Kinakuta",
            "One does not artlessly take a carriage into Ruritania",
            "One does not ordinarily jaunt into San Theodoros",
            "One does not commonly hit the road into Molvanîa",
            "One does not easily airing into Idris",
            "One does not sincerely step into The Greater East Asia Co-Prosperity Sphere",
            "One does not guilelessly hoof it into Grinlandia",
            "One does not guilelessly foot into Kolechia",
            "One does not ordinarily march into Sierra Gordo",
            "One does not frankly jaunt into Kraplakistan",
        ]
        grammar_induction.induce_grammar_using_template_trees(
            dataset,
            words_per_slot=1,
            prune_redundant=True,
            relative_similarity_threshold=0.01,
            max_depth=2,
            minimal_variables=True,
        )


if __name__ == "__main__":
    unittest.main()
