# GlobalBench

GlobalBench is a benchmark for global progress in language technology.
If you are interested in seeing the benchmark, please visit the site:
* [GlobalBench Leaderboard Site](https://explainaboard.inspiredco.ai/benchmark?id=globalbench)

GlobalBench is created by Catherine Cui, [Pengfei Liu](http://pfliu.com/), [Graham Neubig](https://phontron.com), and many collaborators.

## What is GlobalBench?

GlobalBench is a leaderboard, but not your ordinary leaderboard. 

In your *ordinary leaderboard*, organizations submit their best systems and try to get state-of-the-art results so they can earn a spot on the top of the leaderboard (until the next state-of-the-art result comes along).

GlobalBench, in contrast is a *collaborative leaderboard*.
We have a metric of how well NLP systems work for many tasks across many languages in the world, and we aim to improve a *global utility* metric that measures how well systems are working. As an intuitive example, take a look at the following graph, which measures the accuracy of question answering over various languages, with the y-axis representing performance, and the x-axis representing the speaker population of each language:

<img width="848" alt="globalbench-qa" src="https://user-images.githubusercontent.com/398875/178317327-0bf89609-3e00-4a5f-823b-e8aa9c541abb.png">

From this we can see two things. First, there are significant disparities in performance of question answering across languages. Second, there are many languages (represented by the red arrow on the right side of the graph), for which there are no results at all!

If we had a really good system for every language in the world, the figure here would be entirely full, and the area under the curve would be "1.0". However, in the figure above you can see that the area under the curve is actually lower, closer to 0.3. This is the "demographic-average utility", one of the main quantities that GlobalBench measures. We can also measure "linguistic-average utility", which doesn't consider the number of speakers and treats each language equally. If you would like more details, please take a look at the [paper](https://arxiv.org/abs/2110.06733) where these metrics were proposed.

The goal of GlobalBench is for all of us to work together as a community to improve these metrics, and in doing so, make better language technology that works for all of the languages in the world. If this sounds exciting to you, please contribute through the methods below!

## Contributing to GlobalBench

You can contribute to GlobalBench in two ways:
1. Contributing systems to existing datasets in GlobalBench
2. Contributing multilingual datasets to GlobalBench

### Adding Systems

GlobalBench is based on [ExplainaBoard](https://explainaboard.inspiredco.ai/), and supports any of the [datasets that ExplainaBoard supports](https://explainaboard.inspiredco.ai/datasets).

If you have built a system on any of these datasets, please contribute them by [submitting a system to ExplainaBoard](https://explainaboard.inspiredco.ai/systems). It's that easy! Once your system is submitted it will be automatically registered on the leaderboard in a bit.

Currently, you will be given credit on the leaderboard page for your system performance, and we're also working on other ways to recognize people for people who *improve* the global utility the most as well.

### Adding Datasets

If you would like to add another dataset to support in GlobalBench, it needs to be added to [DataLab](https://github.com/expressai/datalab), which ExplainaBoard uses to grab its datasets.

We have [separate directions](https://github.com/ExpressAI/DataLab/blob/main/docs/SDK/add_new_datasets_into_sdk.md) on how to do so on the DataLab site, so please take a look there.

## Contact/Citation

If you're interested in contributing to GlobalBench, please submit datasets or systems through the directions above!
If there is anything you're unsure about, please feel free to leave an issue on this repository and we'll be happy to help.

If you would like to cite the ideas behind GlobalBench in a scientific paper, you can cite the following paper (for now, until we have one citing the benchmark itself with all the contributors!):
```
@inproceedings{blasi22acl,
    title = {Systematic Inequalities in Language Technology Performance across the World’s Languages},
    author = {Damian E Blasi and Antonios Anastasopoulos and Graham Neubig},
    booktitle = {Annual Conference of the Association for Computational Linguistics (ACL)},
    address = {Dublin, Ireland},
    month = {May},
    url = {https://arxiv.org/abs/2110.06733},
    year = {2022}
}
```
