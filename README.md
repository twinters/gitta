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

Which in turn generates all these texts:
```
{"dogs are not supposed to be in the zoo",
"cats are not supposed to be in a salad",
"I like geese and cats",
"cats are not supposed to be in the zoo", 
bananas are not supposed to be in a salad",
"I like dogs and dogs",
"bananas are not supposed to be in the zoo",
"I like dogs and bananas",
"geese are not supposed to be in the zoo",
"geese are not supposed to be in a salad",
"I like cats and dogs",
"I like dogs and geese",
"I like cats and bananas",
"I like bananas and dogs",
"I like bananas and bananas",
"I like cats and geese",
"I like geese and dogs",
"I like dogs and cats",
"I like geese and bananas",
"I like bananas and geese",
"dogs are not supposed to be in a salad",
"I like cats and cats",
"I like geese and geese",
"I like bananas and cats"}
```

## Performance

We tested out this grammar induction algorithm on Twitterbots using the [Tracery](https://tracery.io/) grammar modelling tool.
Gitta only saw either 25, 50 or 100 example generations, and had to introduce a grammar that could generate similar texts.
Every setting was run 5 times, and the median number of in-language texts (generations that were also produced by the original grammar) and not in-language texts (texts that the induced grammar generated, but not the original grammar). The median number of production rules is also included, to show its generalisation performance.

|     Grammar     |               |      | 25 examples |             |      | 50 examples |             |      | 100 examples |             |      |
|:---------------:|---------------|------|:-----------:|-------------|------|:-----------:|-------------|------|-------------|-------------|------|
| Name            | # generations | size | in lang     | not in lang | size | in lang     | not in lang | size | in lang     | not in lang | size |
| botdoesnot      | 380292        | 363  | 648         | 0           | 64   | 2420        | 0           | 115  | 1596        | 4           | 179  |
| BotSpill        | 43452         | 249  | 75          | 0           | 32   | 150         | 0           | 62   | 324         | 0           | 126  |
| coldteabot      | 448           | 24   | 39          | 0           | 38   | 149         | 19          | 63   | 388         | 9           | 78   |
| hometapingkills | 4080          | 138  | 440         | 0           | 48   | 1184        | 3240        | 76   | 2536        | 7481        | 106  |
| InstallingJava  | 390096        | 95   | 437         | 230         | 72   | 2019        | 1910        | 146  | 1156        | 3399        | 228  |
| pumpkinspiceit  | 6781          | 6885 | 25          | 0           | 26   | 50          | 0           | 54   | 100         | 8           | 110  |
| SkoolDetention  | 224           | 35   | 132         | 0           | 31   | 210         | 29          | 41   | 224         | 29          | 49   |
| soundesignquery | 15360         | 168  | 256         | 179         | 52   | 76          | 2           | 83   | 217         | 94          | 152  |
| whatkilledme    | 4192          | 132  | 418         | 0           | 45   | 1178        | 0           | 74   | 2646        | 0           | 108  |
| Whinge_Bot      | 450805        | 870  | 3092        | 6           | 80   | 16300       | 748         | 131  | 59210       | 1710        | 222  |


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
