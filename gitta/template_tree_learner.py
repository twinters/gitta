from abc import abstractmethod
from queue import PriorityQueue
from typing import List, Collection, Set, Dict

from nltk import word_tokenize

from gitta.template import Template
from gitta.template_tree import TemplateTree


# LATTICE
class MergeCandidate:
    def __init__(
        self, t1: Template, t2: Template, distance: int, merged: Template = None,
    ):
        self._t1 = t1
        self._t2 = t2
        self._distance = distance
        self._merged = merged

    def get_templates(self) -> List[Template]:
        return [self._t1, self._t2]

    def get_distance(self) -> int:
        return self._distance

    def get_merged_template(self, minimal_variables: bool = True) -> Template:
        if not self._merged:
            self._merged = _merge_templates(
                self._t1, self._t2, minimal_variables=minimal_variables
            )
        return self._merged

    def is_still_valid(self, unmerged_template: Collection[Template]):
        return self._t1 in unmerged_template and self._t2 in unmerged_template

    def __lt__(self, other: "MergeCandidate"):
        return self._distance < other._distance

    def __gt__(self, other: "MergeCandidate"):
        return self._distance > other._distance

    def __str__(self):
        return (
            "MergeCandidate("
            + str(self._t1)
            + ", "
            + str(self._t2)
            + ", "
            + str(self._distance)
            + ((", " + str(self._merged)) if self._merged else "")
            + ")"
        )

    def __repr__(self):
        return str(self)


class LearnerState:
    def __init__(self, active_templates: Collection[Template]):
        self._active_templates = set(active_templates)
        self._template_children: Dict[Template, Set[Template]] = dict()
        self._built_trees: Dict[Template, TemplateTree] = dict()

    def add_merge_candidate(
        self, merge_candidate: MergeCandidate, minimal_variables: bool
    ):
        self.add_parent(
            merge_candidate.get_merged_template(minimal_variables),
            merge_candidate.get_templates(),
        )

    def add_parent(self, parent: Template, children: Collection[Template]):
        # Check if parent should be made active and added to dictionary
        if parent not in self._template_children:
            self._active_templates.add(parent)
            self._template_children[parent] = set()

        # Deactivate children, and add them to their parent
        for child in children:
            # If child is not the same as parent
            if child != parent:
                # Remove the child from the active templates
                if child in self._active_templates:
                    self._active_templates.remove(child)

                # Add the child to the children of the parent
                self._template_children[parent].add(child)

    def get_active_templates(self) -> Collection[Template]:
        """ Returns templates that still have to be merged """
        return self._active_templates

    def has_multiple_active_templates(self):
        """ Returns true if there are still templates to merge """
        return len(self._active_templates) > 1

    def build_tree(self):
        assert len(self._active_templates) == 1

        root = list(self._active_templates)[0]
        return self.build_tree_for_template(root)

    def build_tree_for_template(self, template: Template) -> TemplateTree:
        """ Converts the learnt state into a template tree for the given template """
        # Check cache
        if template in self._built_trees:
            return self._built_trees[template]

        # If no children, just childless template tree
        if template not in self._template_children:
            resulting_tree = TemplateTree(template)
        else:
            # If children, first convert children
            children: Set[TemplateTree] = {
                self.build_tree_for_template(c)
                for c in self._template_children[template]
            }

            descendants = {
                desc
                for descs in [c.get_strict_descendants() for c in children]
                for desc in descs
            }

            children_without_already_included_descendants = children.difference(
                descendants
            )

            resulting_tree = TemplateTree(
                template, children_without_already_included_descendants
            )

        # Cache built tree
        self._built_trees[template] = resulting_tree

        return resulting_tree

    def is_valid_merge_candidate(self, merge_candidate: MergeCandidate):
        return merge_candidate.is_still_valid(self._active_templates)

    def __str__(self) -> str:
        return (
            "LearnerState("
            + str(self._active_templates)
            + ", "
            + str(self._template_children)
            + ")"
        )

    def __repr__(self):
        return str(self)


class TemplateTreeLearner:
    @abstractmethod
    def learn(self, lines: Collection[str]):
        raise Exception("Not implemented")


class TemplateLatticeLearner(TemplateTreeLearner):
    def __init__(
        self,
        minimal_variables: bool = True,
        words_per_leaf_slot: int = 1,
        use_best_merge_candidate=True,
    ):
        self._minimal_variables = minimal_variables
        self._use_best_merge_candidate = use_best_merge_candidate
        self._words_per_slot = words_per_leaf_slot

    def _is_allowed_distance_from_min_for_leaf_slot(self, min_distance, other_distance):
        return other_distance <= min_distance + self._words_per_slot - 1

    def _is_allowed_distance_from_min_for_non_terminal_slot(
        self, min_distance, other_distance
    ):
        return min_distance == other_distance

    def learn(self, lines: Collection[str]) -> TemplateTree:
        if len(lines) == 0:
            raise Exception("Empty lines were given as input")

        # Hold all current template trees, initially all lines as templates in tree nodes without children.
        learner_state = LearnerState(_to_templates(lines))

        # Make queue of the next best tree duos to merge
        queue: PriorityQueue[MergeCandidate] = PriorityQueue()

        # Fill queue with all combinations of trees with their distance
        initial_pairs = self._create_initial_merge_candidates(
            learner_state.get_active_templates()
        )
        for pair in initial_pairs:
            queue.put(pair)

        first_iteration = True

        # Keep going until you have one tree left
        while learner_state.has_multiple_active_templates():
            assert not queue.empty()

            # Find all trees with the top distance
            top = queue.get()
            current_mergeables = {top}
            while not queue.empty() and self.is_allowed_distance(
                top.get_distance(), _peek(queue).get_distance(), first_iteration
            ):
                merge_candidate = queue.get()
                # Only add the candidate if both trees are still unmerged before this iteration
                if learner_state.is_valid_merge_candidate(merge_candidate):
                    current_mergeables.add(merge_candidate)

            first_iteration = False

            # Add all current mergeables to the learning state
            for merge_candidate in current_mergeables:
                # Add new merges
                learner_state.add_merge_candidate(
                    merge_candidate, minimal_variables=self._minimal_variables
                )

            # Merge all trees with the same top distance
            new_templates: List[Template] = list(
                set(self._merge_all_candidate_templates(current_mergeables))
            )
            # UPDATE PRIORITY QUEUE
            new_merge_candidates = self._create_merge_candidates(
                new_templates, learner_state.get_active_templates(),
            )
            for new_merge_candidate in new_merge_candidates:
                queue.put(new_merge_candidate)

        # Return the one template tree that is remaining
        return learner_state.build_tree()

    def _create_merge_candidates(
        self,
        new_templates: List[Template],
        active_template_trees: Collection[Template],
    ) -> List[MergeCandidate]:
        """
        Creates all merge candidates between the new trees and the active trees, and between new trees themselves
        """
        active_template_trees_list = list(active_template_trees)

        merge_candidates: List[MergeCandidate] = []

        # For every new tree, create candidate for all closest active trees
        for i in range(len(new_templates)):
            nt = new_templates[i]
            other_templates: List[Template] = list(
                set(new_templates[i + 1 :] + active_template_trees_list)
            )
            min_candidates = self._get_merge_candidates_for_templates(
                nt, other_templates
            )

            for mc in min_candidates:
                merge_candidates.append(mc)

        return merge_candidates

    def _create_initial_merge_candidates(
        self, all_templates: Collection[Template],
    ) -> List[MergeCandidate]:
        """
        Creates collection of candidate lists from all initial template trees to each other.
        Assumes that there are no slots in the initial trees
        Only includes the trees with minimal distance from the tree, for every tree
        Only includes MergeCandidate(T_i, T_j) if i < j
        """
        result: List[MergeCandidate] = []

        templates = list(set(all_templates))
        number_of_trees = len(templates)
        for i in range(number_of_trees):
            ti: Template = templates[i]
            min_distance = None
            min_distance_trees = []

            for j in range(i + 1, number_of_trees):
                tj: Template = templates[j]
                if ti != tj:
                    # distance = _get_template_strings_distance(ti, tj)
                    distance = self._get_best_merge_candidate(ti, tj).get_distance()
                    if min_distance is None or distance < min_distance:
                        min_distance = distance
                        min_distance_trees = [(distance, tj)] + [
                            (d, c)
                            for (d, c) in min_distance_trees
                            if self._is_allowed_distance_from_min_for_leaf_slot(
                                min_distance, d
                            )
                        ]
                    elif (
                        min_distance is None
                        or self._is_allowed_distance_from_min_for_leaf_slot(
                            min_distance, distance
                        )
                    ):
                        min_distance_trees.append((distance, tj))

            merge_candidates = [
                MergeCandidate(ti, tree, d) for (d, tree) in min_distance_trees
            ]

            # Add all minimally distant to result
            for mc in merge_candidates:
                result.append(mc)

        return result

    def _get_merge_candidates_for_templates(
        self, template: Template, other_templates: Collection[Template]
    ) -> List[MergeCandidate]:
        min_candidates: List[MergeCandidate] = []
        min_distance = None

        if self._use_best_merge_candidate:
            candidate_finder = self._get_best_merge_candidate
        else:
            candidate_finder = self._get_any_merge_candidate

        for other_template in other_templates:
            if other_template != template:
                # Find best merge between two templates to know best fit
                best_merge = candidate_finder(template, other_template)
                distance = best_merge.get_distance()
                if min_distance is None or distance < min_distance:
                    min_distance = distance
                    min_candidates = [best_merge] + [
                        c
                        for c in min_candidates
                        if self._is_allowed_distance_from_min_for_non_terminal_slot(
                            min_distance, c.get_distance()
                        )
                    ]
                elif (
                    min_distance is None
                    or self._is_allowed_distance_from_min_for_non_terminal_slot(
                        min_distance, distance
                    )
                ):
                    min_candidates.append(best_merge)

        return min_candidates

    def _get_best_merge_candidate(self, t1: Template, t2: Template) -> MergeCandidate:
        """
        Calculates the distance between two given templates, that can contain slots
        """
        max_length = max(t1.get_number_of_non_slots(), t2.get_number_of_non_slots())
        min_slots = min(t1.get_number_of_slots(), t2.get_number_of_slots())

        merged_templates = set(
            Template.merge_templates_wagner_fischer(
                t1, t2, minimal_variables=self._minimal_variables
            )
        )
        merge_candidates = []
        for merged_template in merged_templates:
            distance = _get_distance_of_merged(merged_template, max_length, min_slots)
            merge_candidates.append(
                MergeCandidate(t1, t2, distance, merged=merged_template)
            )
        return min(merge_candidates)

    def _get_any_merge_candidate(self, t1: Template, t2: Template) -> MergeCandidate:
        """ Unused version of _get_best_merge_candidate, but might be prefered for performance gains """
        max_length = max(t1.get_number_of_non_slots(), t2.get_number_of_non_slots())
        min_slots = min(t1.get_number_of_slots(), t2.get_number_of_slots())
        merged_template = next(
            Template.merge_templates_wagner_fischer(
                t1, t2, minimal_variables=self._minimal_variables
            )
        )
        return MergeCandidate(
            t1, t2, _get_distance_of_merged(merged_template, max_length, min_slots)
        )

    def _merge_all_candidate_templates(
        self, merge_candidates: Collection[MergeCandidate],
    ) -> List[Template]:
        """ Merges all mergeables to new trees """
        return [
            candidate.get_merged_template(minimal_variables=self._minimal_variables)
            for candidate in merge_candidates
        ]

    def is_allowed_distance(self, min_distance, other_distance, first_iteration):
        if first_iteration:
            return self._is_allowed_distance_from_min_for_leaf_slot(
                min_distance, other_distance
            )
        else:
            return self._is_allowed_distance_from_min_for_non_terminal_slot(
                min_distance, other_distance
            )


# HELPERS


def _get_distance_of_merged(
    merged_template: Template, max_length: int, min_slots: int
) -> int:
    length_diff = max_length - merged_template.get_number_of_non_slots()
    slot_diff = merged_template.get_number_of_slots() - min_slots
    return length_diff + slot_diff


def _peek(priority_queue: PriorityQueue) -> MergeCandidate:
    return priority_queue.queue[0]


def _to_template_trees(lines: Collection[str]) -> List[TemplateTree]:
    template_trees = [
        TemplateTree(template=template, children=[],)
        for template in _to_templates(lines)
    ]
    return template_trees


def _to_templates(lines: Collection[str]) -> List[Template]:
    templates = [
        Template.from_string(line.strip(), tokenizer=word_tokenize) for line in lines
    ]
    return templates


# def _get_template_strings_distance(template: Template, other: Template) -> int:
#     """
#      Calculates Levenshtein distance between the two templates.
#      Assumes that both template do not contain slots
#      """
#     assert len(template.get_slots()) == 0
#     assert len(other.get_slots()) == 0
#     return editdistance.eval(template.get_elements(), other.get_elements())


# def _calculate_pairwise_distances_levenshtein(templated_data: List[Template]):
#     def convert_datapoint(datapoint) -> Template:
#         return templated_data[int(datapoint[0])]
#
#     def template_distance_datapoint(point1, point2):
#         return _get_template_strings_distance(
#             convert_datapoint(point1), convert_datapoint(point2),
#         )
#
#     number_range = np.arange(len(templated_data)).reshape(-1, 1)
#     return pairwise_distances(
#         number_range, number_range, metric=template_distance_datapoint
#     )


def _merge_template_trees(
    child1: TemplateTree, child2: TemplateTree, minimal_variables
) -> TemplateTree:
    new_template_tree = TemplateTree(
        template=_merge_templates(
            child1.get_template(), child2.get_template(), minimal_variables
        ),
        children=[child1, child2],
    )
    return new_template_tree


def _merge_templates(t1: Template, t2: Template, minimal_variables: bool) -> Template:
    return next(
        Template.merge_templates_wagner_fischer(
            t1, t2, minimal_variables=minimal_variables
        )
    )


def visualise_template_tree_history(template_trees: List[TemplateTree]):
    result = ""
    for i in range(len(template_trees)):
        tree = template_trees[i]
        if len(tree.get_children()):
            children_visualisation = []
            children = list(tree.get_children())
            children.sort(key=lambda c: template_trees.index(c))
            for child in children:
                children_visualisation.append(
                    str(template_trees.index(child)) + ": " + str(child.get_template())
                )
            result += ("\n  +   \n".join(children_visualisation)) + "\n  ==>   \n"
            result += str(i) + ": " + str(tree.get_template()) + "\n\n\n"

    return result
