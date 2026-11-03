# Citing flybots and publication plans

## What flybots is for

flybots is a framework to **build on**. Its purpose is to make complex
autonomy algorithms approachable — something you can read, run, change and
explain — rather than a black box you call.

Every algorithm is implemented once, in plain NumPy, next to the paper it
comes from. Around it the framework gives you the rest of what it takes to
understand a method: a runnable simulation that shows it working, tests that
assert on flight behaviour rather than array shapes, and a documentation page
that explains the idea and its failure modes. Adding your own algorithm means
getting all of that for it too — [Build on flybots](./extending) walks
through adding one end to end.

## How to cite

The repository carries a machine-readable
[`CITATION.cff`](https://github.com/guilyx/flybots/blob/main/CITATION.cff).
GitHub turns it into a **Cite this repository** button on the repository
page, with APA and BibTeX ready to copy, and reference managers such as
Zotero read it directly.

If you prefer to write the entry yourself:

```bibtex
@software{flybots,
  author  = {Lejeune, Erwin},
  title   = {flybots: flight algorithms for autonomous UAVs, from scratch},
  url     = {https://github.com/guilyx/flybots},
  license = {MIT},
  year    = {2026},
  version = {<the version you used>},
}
```

`flybots --version` prints the version you have installed. Pinning it in the
citation matters: the algorithms are corrected as bugs are found, and a
reader should be able to get back to the code you actually ran.

### Cite the algorithms too

flybots is an implementation, not the origin, of the methods in it. Each
module's docstring cites the paper or book its algorithm comes from, and
each simulation page in the [algorithm atlas](/simulations/) lists its
reference. If your work relies on a specific method — the UKF, RRT\*, a
control barrier function — cite that source as well as flybots.

## Publication plan

We intend to publish flybots as a peer-reviewed software paper.

| | |
|---|---|
| **Primary target** | [Journal of Open Source Education](https://jose.theoj.org/) (JOSE) — publishes open-source software and materials for teaching and learning |
| **Fallback** | [Journal of Open Source Software](https://joss.theoj.org/) (JOSS) |

Both review openly on GitHub, are free to publish and to read, and assign a
DOI. JOSE fits the project's purpose best: flybots is built to teach how
these algorithms work, not to introduce new ones.

### Where it stands

- [x] OSI-approved licence (MIT), public repository, published on PyPI
- [x] User documentation, a test suite, and continuous integration
- [x] Contribution guidelines and a code of conduct
- [x] Machine-readable citation metadata (`CITATION.cff`)
- [ ] An archived release with a DOI (Zenodo)
- [ ] The paper itself: `paper.md` and its bibliography
- [ ] The AI-usage disclosure both journals require
- [ ] A pre-submission scope enquiry to the editors

### Contributing to it

The best way to strengthen the submission is the same as the best way to
improve flybots: implement an algorithm properly, with its citation, its
simulation, behavioural tests and a page that explains it. See
[CONTRIBUTING.md](https://github.com/guilyx/flybots/blob/main/CONTRIBUTING.md)
for the bar a new algorithm has to clear.

Authorship of the paper will follow the journal's policy. If you have
contributed substantially and would like to be involved, say so in a
[discussion](https://github.com/guilyx/flybots/discussions).
