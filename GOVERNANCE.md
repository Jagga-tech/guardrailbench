# Governance

GuardrailBench is a vendor-neutral benchmark. This page says who decides what, and how the results are kept trustworthy.

## Roles

- **Maintainers** review changes, write and hold the official split, run official rounds, and publish results. The maintainer list goes in `.github/CODEOWNERS`; see [Status](README.md#status).
- **Contributors** send code, adapters, case reports, and practice results. Anyone can contribute under [CONTRIBUTING.md](CONTRIBUTING.md).
- **Participating vendors** are makers who have asked for their product to be in an official round. They can report anomalies, supply an adapter fix, and state their training sources. They do not get a vote on results.

## How decisions are made

Day-to-day changes are decided in pull requests by maintainer approval. Changes to scoring, the case format, the adapter rules, or this page need an open issue first and at least a week for comment. Maintainers aim for consensus. If there is none, the maintainers vote and the reasoning is written in the issue. A change that alters published scores is recorded in the changelog and versioned.

## Conflict of interest

- Any maintainer affiliation with a vendor is disclosed. The vendor's results row carries a one-line disclosure.
- An affiliated product runs through the same harness as every other product. It gets no early access to cases, including the official split.
- An affiliated maintainer recuses from decisions about that product: its adapter review, its results, and any dispute about them.
- The aim is for an outside party to hold the official split. Until then, the affiliated product's training data is scanned for canary strings and the result is published, and the round where an affiliated product first appears is audited by an independent reviewer.

## Vendor participation rules

There are two ways to take part. Both are free.

- **Practice (open).** A maker runs its own product on the public practice split and sends the results, with full per-case logs, by pull request. Maintainers check the logs and merge. These results are shown on the "Practice (self-reported)" tab and are marked self-reported. See [submit results](docs/guides/submit.md).
- **Official rounds (closed).** The official tabs show only results from the maintainers' closed test on the official split. How a round is run is in [docs/official-runs.md](docs/official-runs.md).

The rules for official rounds follow the spirit of the AMTSO testing standards:

- **Opt-in.** A product enters an official round only when its maker asks. The maintainers do not test a product uninvited. An adapter in this repository lets anyone run that product on the practice split. It does not put the product in a round.
- **How to ask.** The maker opens a [participation request](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml), has a public adapter for the product in this repository, and gives the maintainers a way to run the product for the round. For a hosted product that is an ordinary account or key, sent privately and never posted in an issue. For a self-hosted product it is install instructions.
- **Terms.** The maker confirms in the request that its terms allow the result to be published.
- **Notice.** A participating vendor is told the window in which the runs happen, and sees its own results before they are published.
- **Free participation.** There is no fee to be tested or to take part.
- **Withdrawal.** A maker can withdraw its request until the round's window opens.
- **No veto.** Once a product has been run in a round its maker asked to join, the maker cannot block publication of the results of a valid run.
- **Anomalies.** If a result looks wrong or caused by harness wiring, it is discussed with the vendor before publication. Real harness bugs are fixed and the run is repeated.
- **Re-runs.** A vendor can ask for a re-run on a new version. The old result stays, marked with its version.

## Funding

No one pays for placement, ranking, or inclusion. Money from a vendor, if ever accepted, is disclosed and never buys access to the official split or a say in results.

## Changes to this page

Edit it by pull request under the rules above.
