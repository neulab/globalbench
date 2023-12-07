# GlobalBench

GlobalBench is a benchmark for global progress in language technology.
GlobalBench is created by [Yueqi Song](https://yueqis.github.io/), Catherine Cui, [Simran Khanuja](https://simran-khanuja.github.io/), [Pengfei Liu](http://pfliu.com/), [Graham Neubig](https://phontron.com), and many collaborators.
This repo contains the implementation details of this paper:

Yueqi Song, Catherine Cui, Simran Khanuja, Pengfei Liu, Fahim Faisal, Alissa Ostapenko, Genta Indra Winata, Alham Fikri Aji, Samuel Cahyawijaya, Yulia Tsvetkov, Antonios Anastasopoulos, Graham Neubig. [*GlobalBench: A Benchmark for Global Progress in Natural Language Processing*](https://arxiv.org/abs/2305.14716). In Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP), Dec 2023.


## What is GlobalBench?

GlobalBench is a leaderboard, but not your ordinary leaderboard. 

In your *ordinary leaderboard*, organizations submit their best systems and try to get state-of-the-art results so they can earn a spot on the top of the leaderboard (until the next state-of-the-art result comes along).

GlobalBench, in contrast is a *collaborative leaderboard*.
We have a metric of how well NLP systems work for many tasks across many languages in the world, and we aim to improve a *global utility* metric that measures how well systems are working. As an intuitive example, take a look at the following graph, which measures the accuracy of question answering over various languages, with the y-axis representing performance, and the x-axis representing the speaker population of each language:

<img width="848" alt="globalbench-qa" src="https://user-images.githubusercontent.com/398875/178317327-0bf89609-3e00-4a5f-823b-e8aa9c541abb.png">

From this we can see two things. First, there are significant disparities in performance of question answering across languages. Second, there are many languages (represented by the red arrow on the right side of the graph), for which there are no results at all!

If we had a really good system for every language in the world, the figure here would be entirely full, and the area under the curve would be "1.0". However, in the figure above you can see that the area under the curve is actually lower, closer to 0.3. This is the "demographic-average utility", one of the main quantities that GlobalBench measures, where we treat each speaker equally. We can also measure "linguistic-average utility", which doesn't consider the number of speakers and treats each language equally. 

We also measure the equity of each system. A lower value of equity indicates that performance of systems is closer to a uniform distribution across languages.

If you would like more details, please take a look at our paper where we detailed calculations for these metrics.

The goal of GlobalBench is for all of us to work together as a community to improve these metrics, and in doing so, make better language technology that works for all of the languages in the world. If this sounds exciting to you, please contribute through the methods below!

## Contributing to GlobalBench

You can contribute to GlobalBench in two ways:
1. Contributing systems to existing datasets in GlobalBench
2. Contributing multilingual datasets to GlobalBench

### Adding Systems

If you have built a system on any of these datasets, please contribute them by submitting a system to GlobalBench through a pull request to this repo. 

### Adding Datasets

If you would like to add another dataset to support in GlobalBench, it needs to be submitted through a pull request to this repo, following our given format. 

### Adding Languages or Tasks.

You will need to contact the administrators to submit new languages or tasks to GlobalBench.

## Contact/Citation

If you're interested in contributing to GlobalBench, please submit datasets or systems through the directions above!
If there is anything you're unsure about, please feel free to leave an issue on this repository and we'll be happy to help.

If you would like to cite the ideas behind GlobalBench in a scientific paper, you can cite our paper:
```
@article{song2023globalbench,
  title={GlobalBench: A Benchmark for Global Progress in Natural Language Processing},
  author={Song, Yueqi and Cui, Catherine and Khanuja, Simran and Liu, Pengfei and Faisal, Fahim and Ostapenko, Alissa and Winata, Genta Indra and Aji, Alham Fikri and Cahyawijaya, Samuel and Tsvetkov, Yulia and others},
  journal={arXiv preprint arXiv:2305.14716},
  year={2023}
}
```
