# Official runs

This page says which tests anyone can run, which tests only the maintainers run, and how a maintainer run is kept fair. No official round has been run yet. The conditions for the first one are at the end.

## Open and closed tests

A result that a vendor produces on its own machines cannot be checked fully, so it is never shown as official.

| Test | Who runs it | Where it is shown |
|---|---|---|
| Practice split, detection | Anyone | Practice tab, marked self-reported until a maintainer re-runs a sample |
| Practice split, consistency and stability | Anyone | Practice tab, marked self-reported |
| Official split, no context | Maintainers only | Official tab |
| Official split, card track | Maintainers only | Official card tab |
| Reliability: load, long inputs, failure behaviour | Maintainers only | Reliability tab |

Load and latency are closed because they depend on the machine and the network. A number measured on a vendor's own hardware cannot be compared with anyone else's.

## How a round works

1. **Freeze.** The official split for the round is frozen and its SHA-256 is published in `cases/OFFICIAL_SHA256` before any product is run.
2. **Notice.** Each vendor is told its product is in the round and the window in which runs happen. The exact day is not announced.
3. **Run.** Every product is run once, with its default configuration, through the public adapter in this repository. Product versions are recorded. Self-hosted products are pinned to a version. Hosted products cannot be pinned, so the run date is recorded.
4. **Review.** Vendors see their own results, as a report without hidden cases (see [what a vendor is told](#what-a-vendor-is-told)), and can report anomalies before publication, as [GOVERNANCE.md](../GOVERNANCE.md) describes. If the harness was wrong, it is fixed and the run is repeated. The first run's logs are kept and the row is marked as a re-run.
5. **Publish and retire.** Scores, the run environment, the round's cases and the per-case logs are published together. Logs can repeat case text, so they are not published before the cases are. The cases move to the practice split, and the next round uses new cases.

Every attempt counts. There is no "best of" run.

## What a vendor is told

**Before a round.** The vendor is told that its product is in the round, the window in which the runs happen, and which adapter in this repository will be used. The exact day is not announced. The adapter is public, so the vendor can read it, run it on the practice split, and send a fix before the window opens. [Add your product](guides/add-your-product.md) shows how to run it.

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

**A vendor could treat the benchmark's traffic differently.** Runs use an ordinary account of the kind any customer gets, where the vendor's terms allow it, and the run day is not announced. We cannot prove that a hosted product did not recognise the run. The stability test, which sends reworded copies of the same cases, gives some evidence, and anyone can compare a published result with the product's behaviour on the retired cases.

**Self-hosted and hosted products cannot share a latency table.** For a self-hosted product the number measures the maintainers' machine. For a hosted product it measures the vendor's service and the network in between. They are reported in separate tables and never ranked against each other. Detection results are not affected.

**A maintainer may be affiliated with a product.** That product is never scored on cases its makers have seen. Its round is run or audited by an independent reviewer, and its row carries the disclosure. The aim is for an outside party to hold the official split for every round. See the conflict-of-interest rules in [GOVERNANCE.md](../GOVERNANCE.md).

## Run environment

- **One machine for all self-hosted products**, with its CPU, GPU, memory and software versions written into the published results. A GPU with 24 GB of memory is enough for the largest model in the current adapter set.
- **One region for all hosted products**, also recorded.
- **Keys** for hosted products are held by the maintainers running the round and are never committed.
- **The official split** is kept in private storage. Only the people running the round can read it.

## Before the first official round

- Human review of the cases, so a "Verified" subset exists.
- A fresh official split that no product has been run on.
- Written permission from each hosted vendor whose terms require it. Products whose terms forbid publication are left out or shown as declined.
- An independent reviewer for any affiliated product.
- A live run of every adapter in the round against the real product. Adapters marked UNVERIFIED in their source are not used for official results.

The first round will cover self-hosted, open-source products, which need no vendor permission and no keys.
