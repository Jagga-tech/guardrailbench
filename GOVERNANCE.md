# Governance

GuardrailBench is a vendor-neutral benchmark. This page says who decides what, and how we keep the results trustworthy.

## Roles

- **Maintainers** review changes, write and hold the official split, run official evaluations, and publish results. Maintainers are listed in CODEOWNERS once the organisation exists.
- **Contributors** send code, adapters, case reports, and unverified results. Anyone can contribute under [CONTRIBUTING.md](CONTRIBUTING.md).
- **Participating vendors** are makers of products we test. They can give notice of anomalies, supply an adapter fix, and state their training sources. They do not get a vote on results.

## How decisions are made

Day-to-day changes are decided in pull requests by maintainer approval. Changes to scoring, the case format, the adapter rules, or this page need an open issue first and at least a week for comment. Maintainers aim for consensus. If there is none, the maintainers vote and the reasoning is written in the issue. A change that alters published scores is recorded in the changelog and versioned.

## Conflict of interest

- Any maintainer affiliation with a vendor is disclosed. The vendor's results row carries a one-line disclosure.
- An affiliated product runs through the same harness as every other product. It gets no early access to cases, including the official split.
- An affiliated maintainer recuses from decisions about that product: its adapter review, its results, and any dispute about them.
- The goal is for an outside party to hold the official split. Until then, the affiliated product's training data is scanned for canary strings and the result is published, and the round where an affiliated product first appears is audited by an independent reviewer.

## Vendor participation rules

These follow the spirit of AMTSO testing standards.

- **Notice.** Vendors are told before their product is tested and before results are published.
- **Free participation.** There is no fee to be tested or to take part.
- **No veto.** A vendor cannot block publication of results from a valid run.
- **Anomalies.** If a result looks wrong or caused by harness wiring, we discuss it with the vendor before publication. Real harness bugs are fixed and the run is repeated.
- **Opt-out.** Where a vendor's terms forbid publishing benchmark results, we honour that. The product shows as declined or is left out.
- **Fixes after publication.** A vendor can ask for a re-run on a new version. The old result stays, marked with its version.

## Funding

No one pays for placement, ranking, or inclusion. Money from a vendor, if ever accepted, is disclosed and never buys access to the official split or a say in results.

## Changes to this page

Edit it by pull request under the rules above.
