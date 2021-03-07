from typing import Collection, Tuple, Optional, Callable, Any

from gitta.context_free_grammar import ContextFreeGrammar
from gitta.slot_name_generator import alphabetic_slot_name_iterator
from gitta.slot_values import SlotValues
from gitta.template_tree import TemplateTree
from gitta.template_tree_learner import TemplateLatticeLearner


def induce_grammar_using_template_trees(
    lines: Collection[str],
    relative_similarity_threshold: float = 1,
    minimal_variables: bool = True,
    words_per_slot: int = 1,
    prune_redundant: bool = True,
    max_recalculation: Optional[int] = None,
    use_best_merge_candidate=True,
    max_depth: Optional[int] = None,
    log_tree: Callable[[str, TemplateTree], None] = lambda text, tt,: None,
):
    # Learn a tree from the given dataset
    learned_tree = TemplateLatticeLearner(
        minimal_variables=minimal_variables,
        words_per_leaf_slot=words_per_slot,
        use_best_merge_candidate=use_best_merge_candidate,
    ).learn(lines)
    log_tree("1. Learned", learned_tree)

    # Prune all redundant children: if all other children of parent cover it, the child is not necessary.
    if prune_redundant:
        learned_tree = learned_tree.prune_redundant_abstractions()
        log_tree("2. Pruned", learned_tree)

    derived_slot_values, simplified_tree = _name_and_simplify_tree(
        learned_tree, relative_similarity_threshold
    )
    log_tree("3. Simplified", learned_tree)

    simplified_tree = simplified_tree.collapse_using_slot_values(derived_slot_values)
    log_tree("4. Collapsed simplified", learned_tree)

    # Keep recalculating the tree until convergence
    new_tt = None
    iteration = 0
    while simplified_tree != new_tt and (
        max_recalculation is None or iteration < max_recalculation
    ):
        if new_tt is not None:
            simplified_tree = new_tt
            log_tree("5 ("+str(iteration)+"). Recalculated", simplified_tree)
        new_tt = simplified_tree.recalculate_templates(
            minimal_variables=minimal_variables
        )
        derived_slot_values, new_tt = _name_and_simplify_tree(
            new_tt, relative_similarity_threshold
        )
        iteration += 1

    # Collapse final tree using the last slot values
    collapsed_tt = simplified_tree.collapse_using_slot_values(derived_slot_values)
    log_tree("6. Collapsed final", collapsed_tt)

    # Limit max depth
    if max_depth is not None:
        collapsed_tt = collapsed_tt.reduce_depth(max_depth)
        log_tree("7. Reduced depth", collapsed_tt)

    # Derive final slot values
    final_slot_values = collapsed_tt.get_slot_values()

    # Create grammar
    grammar = ContextFreeGrammar.from_slot_values(
        collapsed_tt.get_template(), final_slot_values,
    )

    return grammar


def _name_and_simplify_tree(
    learned_tree: TemplateTree, relative_similarity_threshold: float
) -> Tuple[SlotValues, TemplateTree]:
    """
    Gives a name to all unnamed slots, and simplifies under the independence between slots assumption
    """
    # Give all slots a unique name
    slot_name_generator = alphabetic_slot_name_iterator()
    named_lattice = learned_tree.name_slots_automatically(slot_name_generator)

    # Find what every slot maps to
    possible_slot_values = named_lattice.get_slot_values()

    # Merge similar slots together, to reduce the number of unique slots
    merged_slot_values = possible_slot_values.merge_slots(
        relative_similarity_threshold=relative_similarity_threshold,
    )

    # Use merged slots to reduce variables in the template tree
    replacements = merged_slot_values.get_replacements()
    merged_slots_tree = named_lattice.name_template_slots(replacements)

    return merged_slot_values, merged_slots_tree


# def induce_grammar_using_template_trees_old(
#     lines: Collection[str],
#     relative_similarity_threshold: float = None,
#     minimal_variables: bool = True,
# ):
#     # Create tree
#     initial_tree = LevenshteinTemplateTreeLearner(
#         minimal_variables=minimal_variables
#     ).learn(lines)
#
#     # Process tree
#     collapsed = initial_tree.collapse()
#     lattice = collapsed.to_lattice()
#
#     named_lattice = lattice.name_slots_automatically()
#
#     # Reduce to context-free grammar and simplify
#     slot_contents = named_lattice.get_descendents_slot_content_mappings()
#     possible_slot_values = SlotValues.from_slot_assignments(slot_contents)
#     merged_slot_values = possible_slot_values.merge_slots(
#             relative_similarity_threshold=relative_similarity_threshold
#     )
#
#     # Use merged slot values to reduce variables
#     merged_slots_tree = named_lattice.name_template_slots(
#         merged_slot_values.get_replacements()
#     )
#
#     collapsed_slots_tree = merged_slots_tree.collapse_using_slot_values(
#         merged_slot_values
#     )
#
#     # Create grammar
#     grammar = ContextFreeGrammar.from_template_tree(
#         collapsed_slots_tree,
#         relative_similarity_threshold=relative_similarity_threshold,
#     )
#
#     return grammar
