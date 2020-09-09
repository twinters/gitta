from queue import LifoQueue, Queue
from typing import List, Tuple, Set, Dict, Collection, Iterator

from gitta.slot_name_generator import alphabetic_slot_name_iterator
from gitta.template import Template
from gitta.slot_values import SlotValues
from gitta.template_elements import TemplateSlot, NamedTemplateSlot, SlotAssignment


class TemplateTree:
    def __init__(self, template: Template, children: Collection["TemplateTree"] = None):
        self._template = template
        self._children = frozenset(children) if children is not None else frozenset()

    # ACCESSORS
    def get_template(self):
        return self._template

    def get_children(self):
        return self._children

    def get_descendants(self):
        return [self] + self.get_strict_descendants()

    def get_strict_descendants(self):
        """ Returns descendants without itself """
        return [desc for child in self._children for desc in child.get_descendants()]

    def get_descendant_leaves(self):
        if len(self._children) == 0:
            return [self]

        # Return flattened list of children descendent leaves
        return [
            item
            for sublist in self._children
            for item in sublist.get_descendant_leaves()
        ]

    def has_slots(self):
        return len(self._template.get_slots()) > 0

    def get_all_descendent_slots_breadth_first(self):
        result = []
        queue: Queue[TemplateTree] = Queue()
        queue.put(self)
        while not queue.empty():
            element = queue.get()
            # Add all slots
            result.extend(element.get_template().get_slots())

            # Add all children to queue
            for c in element.get_children():
                queue.put(c)

        return result

    def get_slot_contents_tuples(self) -> Set[Tuple[Template]]:
        return {
            self._template.extract_content(child._template) for child in self._children
        }

    def get_slot_content_mappings(self, tuples=None) -> Set[SlotAssignment]:
        result = set()
        template_slots = self._template.get_slots()
        if tuples is None:
            tuples = self.get_slot_contents_tuples()
        for tup in tuples:
            result.add(self._template.create_slot_mapping(tup, template_slots))
        return result

    def get_slot_values(self) -> SlotValues:
        """
        Calculates the slot values of every slot of the template.
        This assumes that slots have independent content
        """
        result = SlotValues()

        for child in self._children:
            # Find the slot values for this child
            slot_values: Dict[
                TemplateSlot, Set[Template]
            ] = self._template.create_slot_values_mapping(child._template)
            result.add_all_slot_values(slot_values)

            # Add slot values of the child
            result.add_all_slot_values(child.get_slot_values())

        return result

    def get_descendents_slot_content_mappings(self) -> Set[SlotAssignment]:
        """ Gets all mappings from every slot from the template to all possible values, by following children until
        the leaves """
        result = set()
        if len(self._children) == 0:
            return result

        for child in self._children:
            # Extract the slots to Tuple[TemplateElement] for this child
            assignment = self._template.extract_content(child._template)

            # Convert this to mapping of slot names to this child's List[TemplateElement] of the Template
            mapping: SlotAssignment = self._template.create_slot_mapping(assignment)

            # Get all of the descendent content mappings
            if child._template.has_slots():
                child_descendents_mapping: Set[
                    SlotAssignment
                ] = child.get_descendents_slot_content_mappings()
                for child_map in child_descendents_mapping:
                    new_mapping = SlotAssignment(mapping)
                    new_mapping.update(child_map)
                    result.add(new_mapping)
            else:
                result.add(mapping)

        return result

    def get_descendent_leaves_slot_content_tuples(self) -> Set[Tuple[Template]]:
        mappings = self.get_descendent_leaves_slot_content_mappings()
        return {
            tuple([mapping[slot] for slot in self._template.get_slots()])
            for mapping in mappings
        }

    def get_descendent_leaves_slot_content_mappings(self) -> Set[SlotAssignment]:
        result = set()
        if len(self._children) == 0:
            return result

        for child in self._children:
            # Extract the slots to Tuple[TemplateElement] for this child
            assignment = self._template.extract_content(child._template)

            # Convert this to mapping of slot names to this child's List[TemplateElement] of the Template
            mapping: SlotAssignment = self._template.create_slot_mapping(assignment)

            # Get all of the descendent content mappings
            if child._template.has_slots():
                child_descendents_mapping: Set[
                    SlotAssignment
                ] = child.get_descendent_leaves_slot_content_mappings()
                for child_map in child_descendents_mapping:
                    new_mapping = SlotAssignment()
                    for key in mapping.keys():
                        new_mapping[key] = mapping[key].fill(child_map)
                    result.add(new_mapping)
            else:
                result.add(mapping)

        return result

    def get_depth(self) -> int:
        return self._get_depth(dict())

    def _get_depth(self, cache: Dict["TemplateTree", int]) -> int:
        if self in cache:
            return cache[self]
        depth = (
            (max(child._get_depth(cache) for child in self._children) + 1)
            if len(self._children) > 0
            else 0
        )
        cache[self] = depth
        return depth

    # CREATORS
    def collapse(self) -> "TemplateTree":
        """ Merges children with itself if the child has the same template as this node """
        if not self._children:
            return self

        new_children_dict = dict()
        for child in self._children:
            child = child.collapse()
            if child._template == self._template:
                for childchild in child._children:
                    # Check if nothing else with this template
                    if childchild.get_template() in new_children_dict:
                        new_children_dict[childchild.get_template()].append(childchild)
                    else:
                        new_children_dict[childchild.get_template()] = [childchild]
            else:
                # Check if nothing else with this template
                if child.get_template() in new_children_dict:
                    new_children_dict[child.get_template()].append(child)
                else:
                    new_children_dict[child.get_template()] = [child]

        new_children = []
        for child_template in new_children_dict:
            template_trees_with_this_template = new_children_dict[child_template]
            if len(template_trees_with_this_template) == 1:
                new_children.append(template_trees_with_this_template[0])
            else:
                new_children_of_this_template = [
                    c._children for c in template_trees_with_this_template
                ]
                flattened_children = [
                    item
                    for sublist in new_children_of_this_template
                    for item in sublist
                ]
                new_children.append(TemplateTree(child_template, flattened_children))
        return TemplateTree(self._template, new_children)

    def calculated_merged_independent_slot_values(
        self, relative_similarity_threshold=1
    ) -> SlotValues:
        slot_values = self.get_slot_values()
        merged_slot_values = slot_values.merge_slots(
            relative_similarity_threshold=relative_similarity_threshold
        )
        return merged_slot_values

    def collapse_using_slot_values(
        self, slot_values: SlotValues = None
    ) -> "TemplateTree":
        """ Collapses the tree given knowledge about what values a slot can have,
        removing unnecessary TemplateTree nodes """

        if slot_values is None:
            slot_values = self.calculated_merged_independent_slot_values()

        collapsed_children: Collection[TemplateTree] = [
            c.collapse_using_slot_values(slot_values) for c in self._children
        ]

        new_children = []
        own_slots = set(self.get_template().get_slots())

        for c in collapsed_children:
            c_slots = set(c.get_template().get_slots())

            # If there is overlap in slots and the template is encompassed
            if len(
                own_slots.intersection(c_slots)
            ) > 0 and self.get_template().encompasses(c.get_template(), slot_values):
                new_children.extend(c.get_children())
            else:
                new_children.append(c)

        return TemplateTree(self.get_template(), new_children)

    def prune_redundant_abstractions(self) -> "TemplateTree":
        """
        Prunes all children whose descendant leaves are all already covered by other children's descendant leaves.
        It also applies this recursively to all children
        """
        pruned_children = [
            child.prune_redundant_abstractions() for child in self._children
        ]
        child_descendant_leaves = [
            (child, child.get_descendant_leaves()) for child in pruned_children
        ]

        # Sort the list so that nodes with less leaf descendants are pruned earlier than those with more
        child_descendant_leaves.sort(key=lambda val: len(val[1]))

        removed_children_indices = set()
        for i in range(len(child_descendant_leaves)):
            if i not in removed_children_indices:
                (child, descendants) = child_descendant_leaves[i]
                other_children_descendants = set()

                for j in range(len(child_descendant_leaves)):
                    if j not in removed_children_indices and i != j:
                        other_children_descendants.update(child_descendant_leaves[j][1])

                if other_children_descendants.issuperset(descendants):
                    removed_children_indices.add(i)

        selected_children = {
            child_descendant_leaves[i][0]
            for i in range(len(child_descendant_leaves))
            if i not in removed_children_indices
        }

        return TemplateTree(self._template, selected_children)

    def to_lattice(self):
        """ Goes over all descendents to see if they would have also fitted under different parents.
        If so, these are added as parents """
        descendants = self.get_descendants()
        new_children: Dict[TemplateTree, List[TemplateTree]] = dict()

        for d in descendants:
            # Go over all nodes of the template tree and check if they could have had other parents as well

            queue: LifoQueue[TemplateTree] = LifoQueue()
            queue.put(self)
            while not queue.empty():
                tt = queue.get()
                tt_children_covering_d = [
                    c
                    for c in tt.get_children()
                    if c.get_template().covers(d.get_template())
                ]

                if len(tt_children_covering_d) > 0:
                    for c in tt_children_covering_d:
                        queue.put(c)
                elif d != tt:
                    # If no children of tt cover the template tree d, then tt was the most specific tt covering this.
                    if tt in new_children:
                        new_children[tt].append(d)
                    else:
                        new_children[tt] = [d]

        new_tt = self.attach_children_recursively(new_children)

        return new_tt

    def attach_children_recursively(
        self,
        new_children_map: Dict["TemplateTree", List["TemplateTree"]],
        new_template_trees: Dict["TemplateTree", "TemplateTree"] = None,
    ):
        # Fix arguments if None is given
        if new_template_trees is None:
            new_template_trees = dict()

        # Check cache
        if self in new_template_trees:
            return new_template_trees[self]

        # Renew all self children, recursively
        new_children = [
            c.attach_children_recursively(new_children_map, new_template_trees)
            for c in self._children
        ]

        # If it has new children to add itself, make sure they're also mapped
        if self in new_children_map:
            new_children += [
                c.attach_children_recursively(new_children_map, new_template_trees)
                for c in new_children_map[self]
            ]
        result = TemplateTree(self._template, new_children)

        # Cache
        new_template_trees[self] = result

        return result

    def name_slots_automatically(
        self, slot_name_generator: Iterator[str] = alphabetic_slot_name_iterator()
    ):
        all_slots = self.get_all_descendent_slots_breadth_first()
        slot_names = {s.get_name() for s in all_slots if s.is_named()}
        unnamed_slots = [s for s in all_slots if not s.is_named()]

        named_slots_map = dict()
        for i in range(len(unnamed_slots)):

            # Make sure the new slot name is not being used in the template tree already
            new_slot_name = None
            while new_slot_name is None or new_slot_name in slot_names:
                new_slot_name = next(slot_name_generator)

            # Create new slot with this name
            named_slots_map[unnamed_slots[i]] = NamedTemplateSlot(new_slot_name)

        return self.name_template_slots(named_slots_map)

    def name_template_slots(
        self,
        slot_map: Dict[TemplateSlot, NamedTemplateSlot],
        new_template_trees: Dict["TemplateTree", "TemplateTree"] = None,
    ) -> "TemplateTree":
        # Fix arguments if None is given
        if new_template_trees is None:
            new_template_trees = dict()
        # Check cache
        if self in new_template_trees:
            return new_template_trees[self]

        result = TemplateTree(
            self._template.name_template_slots(slot_map),
            [
                c.name_template_slots(slot_map, new_template_trees)
                for c in self._children
            ],
        )

        # Cache
        new_template_trees[self] = result

        return result

    def recalculate_templates(self, minimal_variables=True):
        return self._recalculate_templates(dict(), minimal_variables)

    def _recalculate_templates(
        self,
        recalculate_cache: Dict["TemplateTree", "TemplateTree"],
        minimal_variables: bool,
    ) -> "TemplateTree":
        # Check if already recalculated
        if self in recalculate_cache:
            return recalculate_cache[self]

        # Map all children
        mapped_children = [
            child._recalculate_templates(recalculate_cache, minimal_variables)
            for child in self._children
        ]
        new_template = (
            Template.merge_all(
                [c.get_template() for c in mapped_children],
                minimal_variables,
                self.get_template(),
            )
            if len(mapped_children) > 0
            else self._template
        )

        # Create new
        result = TemplateTree(new_template, mapped_children)

        # Cache
        recalculate_cache[self] = result

        return result

    def reduce_depth(self, depth) -> "TemplateTree":
        """ Reduces the depth of the tree, leaving only the bottom depth nodes """
        # Calculate depths of all children
        depths: Dict[TemplateTree, int] = dict()
        self._get_depth(depths)

        new_children = self._get_top_descendants_with_max_depth(depth - 1, depths)
        return TemplateTree(self.get_template(), new_children)

    def _get_top_descendants_with_max_depth(
        self, depth: int, depths: Dict["TemplateTree", int]
    ) -> Collection["TemplateTree"]:
        top_descendants = []
        for child in self._children:
            if depths[child] <= depth:
                top_descendants.append(child)
            else:
                child_top_descendants = child._get_top_descendants_with_max_depth(
                    depth, depths
                )
                top_descendants.extend(child_top_descendants)
        return top_descendants

    # Hash and Equals
    def __eq__(self, other: object) -> bool:
        if isinstance(other, TemplateTree):
            return self is other or (
                self._template == other._template and self._children == other._children
            )
        return False

    def __hash__(self) -> int:
        return hash((self._template, self._children))

    # String representation

    def __str__(self):
        return str(self._template) + self._get_children_str()

    def _get_children_str(self):
        return (
            " {" + self._get_sorted_children_string() + "}"
            if len(self._children) > 0
            else ""
        )

    def _get_sorted_children_string(self):
        children = list(self._children)
        children.sort(key=lambda x: str(x))
        return " | ".join(str(child) for child in children)

    def __repr__(self):
        return self.__str__()
