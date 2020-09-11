# Gitta

[Gitta](https://arxiv.org/abs/2009.04530) (*"Grammar Induction using a Template Tree Approach"*) is a method for inducing context-free grammars.
It performs particularly well on datasets that have latent templates, e.g. forum topics, writing prompts and output from template-based text generators.
The found context-free grammars can easily be converted into grammars for use in grammar languages such as [Tracery](https://tracery.io/) & [Babbly](https://github.com/twinters/babbly).

## Demo

A demo for Gitta can be found & executed on [Google Colaboratory](https://colab.research.google.com/drive/1uD2tRUrXBtHm0YYWM7vuDivjacLq7K0G?usp=sharing).

## Example

```
dataset = [
    "I like cats and dogs",
    "I like bananas and geese",
    "I like geese and cats",
    "bananas are not supposed to be in a salad",
    "geese are not supposed to be in the zoo",
]
induced_grammar = grammar_induction.induce_grammar_using_template_trees(
    dataset,
    relative_similarity_threshold=0.1,
)
print(induced_grammar)
print(induced_grammar.generate_all())
```
Outputs as grammar:
```
{
    "origin": [
        "<B> are not supposed to be in <C>",
        "I like <B> and <B>"
    ],
    "B": [
        "bananas",
        "cats",
        "dogs",
        "geese"
    ],
    "C": [
        "a salad",
        "the zoo"
    ]
}
```

And as generations:
```
{"dogs are not supposed to be in the zoo", "cats are not supposed to be in a salad", "I like geese and cats", "cats are not supposed to be in the zoo", "bananas are not supposed to be in a salad", "I like dogs and dogs", "bananas are not supposed to be in the zoo", "I like dogs and bananas", "geese are not supposed to be in the zoo", "geese are not supposed to be in a salad", "I like cats and dogs", "I like dogs and geese", "I like cats and bananas", "I like bananas and dogs", "I like bananas and bananas", "I like cats and geese", "I like geese and dogs", "I like dogs and cats", "I like geese and bananas", "I like bananas and geese", "dogs are not supposed to be in a salad", "I like cats and cats", "I like geese and geese", "I like bananas and cats"}
```


## Paper citation

If you would like to refer to this work, or if use this work in an academic context, please consider citing [the following paper](https://arxiv.org/abs/2009.04530):

```
@article{winters2020gitta,
    title={Discovering Textual Structures: Generative Grammar Induction using Template Trees},
    author={Winters, Thomas and De Raedt, Luc},
    journal={Proceedings of the 11th International Conference on Computational Creativity},
    pages = {177-180},
    year={2020},
    publisher={Association for Computational Creativity}
}
```

Or APA style:
```
Winters, T., & De Raedt, L. (2020). Discovering Textual Structures: Generative Grammar Induction using Template Trees. Proceedings of the 11th International Conference on Computational Creativity.
```
