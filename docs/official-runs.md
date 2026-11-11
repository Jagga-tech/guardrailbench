# Official rounds

This page is the run policy. It says which tests anyone can run, which tests only the maintainers run, how a product gets into an official round, and how a round is kept fair. No official round has been run. The conditions for the first one are at the end.

## Open and closed tests

A result that a vendor produces on its own machines cannot be checked fully, so it is never shown as official.

| Test | Who runs it | Where it is shown |
|---|---|---|
| Practice split, detection | Anyone | "Practice (self-reported)" tab, marked self-reported |
| Practice split, consistency and stability | Anyone | "Practice (self-reported)" tab, marked self-reported |
| Official split, no-context track | Maintainers only, for products whose makers asked | "Official · No context" tab |
| Official split, card track | Maintainers only, for products whose makers asked | "Official · Card" tab |
| Reliability: load, long inputs, failure behaviour | Maintainers only, for products whose makers asked | "Reliability" tab |

Load and latency are closed because they depend on the machine and the network. A number measured on a vendor's own hardware cannot be compared with anyone else's.

## How a product enters a round

A product is in an official round only when its maker asks. The maintainers do not test a product uninvited. An adapter in this repository does not put a product in a round: it only lets anyone run that product on the practice split.

To ask, the maker does three things:

1. **Opens a participation request.** Use the [participation request form](https://github.com/Jagga-tech/guardrailbench/issues/new?template=participation.yml). It asks for the product, the maker, whether it is hosted or self-hosted, the adapter, the tracks wanted and a contact route. The maker confirms that its terms allow the result to be published and that it accepts this policy.
2. **Has a public adapter in this repository.** Either one that is already here or one the maker adds by pull request. [Add your product](guides/add-your-product.md) shows how.
3. **Gives the maintainers a way to run the product for the round.** For a hosted product: an ordinary account or key of the kind any customer gets, sent privately through the contact route. Never post a key in an issue or a pull request. For a self-hosted product: install instructions that work on a clean machine.

A maker can withdraw its request until the round's window opens. After its product has been run, the results of a valid run are published.

## How a round works

1. **Freeze.** The official split for the round is frozen and its SHA-256 is published in `cases/OFFICIAL_SHA256` before any product is run.
2. **Notice.** The round covers the products whose makers have asked to take part and met the three conditions above. Each participating vendor is told the window in which runs happen. The exact day is not announced.
3. **Run.** Every product in the round is run once, with its default configuration, through the public adapter in this repository. Product versions are recorded. Self-hosted products are pinned to a version. Hosted products cannot be pinned, so the run date is recorded.
4. **Review.** Vendors see their own results, as a report without hidden cases (see [what a vendor is told](#what-a-vendor-is-told)), and can report anomalies before publication, as [GOVERNANCE.md](../GOVERNANCE.md) describes. If the harness was wrong, it is fixed and the run is repeated. The first run's logs are kept and the row is marked as a re-run.
5. **Publish and retire.** Scores, the run environment, the round's cases and the per-case logs are published together. Logs can repeat case text, so they are not published before the cases are. The cases move to the practice split, and the next round uses new cases.

Every attempt counts. There is no "best of" run.

## What a vendor is told

**Before a round.** A vendor that has asked to take part is told the window in which the runs happen and which adapter in this repository will be used. The exact day is not announced. The adapter is public, so the vendor can read it, run it on the practice split, and send a fix before the window opens. [Add your product](guides/add-your-product.md) shows how to run it.

**After the run, before publication.** The vendor gets a report on its own product, made with `guardrailbench vendor-report` (see [the command line reference](reference/cli.md#vendor-report)). It holds:

- the headline numbers with their intervals, the same ones `score` computes;
- counts and rates by checkpoint, attack family, sector, twin change, mode (native or flattened) and outcome (correct, over-block, miss, inverted);
- for each attack family and checkpoint where the product missed attacks or stopped benign twins, the ids of public practice cases the product got wrong in the same way. These come from the product's run on the practice split, so the vendor can reproduce that kind of failure on cases it is allowed to see. If no practice case failed that way, the report says so.

The report holds no hidden case: no id, no text, no deployment card and no product response. The command has no option to add them.

**Disputes.** If a vendor thinks a group of results is wrong, it says which group and why. A maintainer who is not affiliated with any product, or the independent reviewer, then checks the cases in that group again.

- If the harness or the adapter was wrong, it is fixed and the run is repeated, as step 4 says.
- If a case has the wrong label, the case is dropped for every product and all scores are computed again.
- A small number of disputed cases may be shown to the vendor, but only if those cases are then retired for every product, so no product is scored on them again. The disclosure is recorded in the published results.

A dispute does not give a vendor a veto. Results from a valid run are published.

**After publication.** When the results are published, the round's cases and all per-case logs are published with them (step 5). The vendor can then see every case and what its product answered.

## Known weak points and what we do about them

**A hosted product sees the hidden cases when it is run.** Its service receives every request and can log it. So a set of hidden cases is hidden for one round only. All products in a round are run inside the same short window, and the cases are retired after it. A product is never scored on cases its vendor has already been sent.

**A vendor could treat the benchmark's traffic differently.** The vendor supplies the account, so it knows which account the run will use. The account must be an ordinary one of the kind any customer gets, and the run day is not announced. We cannot prove that a hosted product did not recognise the run. The stability test, which sends reworded copies of the same cases, gives some evidence, and anyone can compare a published result with the product's behaviour on the retired cases.

**Self-hosted and hosted products cannot share a latency table.** For a self-hosted product the number measures the maintainers' machine. For a hosted product it measures the vendor's service and the network in between. They are reported in separate tables and never ranked against each other. Detection results are not affected.

**A maintainer may be affiliated with a product.** That product is never scored on cases its makers have seen. Its round is run or audited by an independent reviewer, and its row carries the disclosure. The aim is for an outside party to hold the official split for every round. See the conflict-of-interest rules in [GOVERNANCE.md](../GOVERNANCE.md).

## Run environment

- **One machine for all self-hosted products**, with its CPU, GPU, memory and software versions written into the published results. A GPU with 24 GB of memory is enough for the largest model in the current adapter set.
- **One region for all hosted products**, also recorded.
- **Keys** for hosted products are supplied privately by the vendor, held by the maintainers running the round, and never committed or posted.
- **The official split** is kept in private storage. Only the people running the round can read it.

## Before the first official round

- Human review of the cases, so that a "Verified" subset exists.
- A fresh official split that no product has been run on.
- A participation request from the maker of every product in the round, with its confirmation that the result may be published.
- A public adapter for every product in the round, and a way for the maintainers to run it: an account or key for a hosted product, install instructions for a self-hosted one.
- An independent reviewer for any affiliated product.
- A live run of every adapter in the round against the real product. Adapters marked UNVERIFIED in their source are not used for official results.
