# thunderid-dx-manager

Tracks the three things that decide whether building on a ThunderID SDK goes well: whether
the SDKs can do what the product asks of them, what is in flight, and what is already
written down as broken.

| Page | What it answers |
|---|---|
| Feature parity | Can every SDK handle everything the product can send it? |
| Pull requests | What is open across the four SDK repositories, and what has gone quiet? |
| DX issues | What is open in `thunder-id/thunderid` under the Developer Experience label? |

Parity is derived from source and is true of a commit. The other two are read from GitHub
when the report is generated and are true of a moment, so they are stamped with that time
rather than a revision.

A flow is assembled from executors and rendered from elements the server sends to the
client. If the server can emit something an SDK does not handle, an application built on
that SDK breaks at the point the user hits that step, and nothing before then says so.
This repository finds those before a user does.

**Report:** https://brionmario.github.io/thunderid-dx-manager/

## What it measures

Six axes, all discovered from source on every run rather than kept in a list:

| Axis | Source of truth |
|---|---|
| Flow executors | `backend/internal/flow/executor` - which ones reach the client, and the inputs each declares |
| Flow input types | `backend/pkg/thunderidengine/providers/constants.go` |
| Flow element types | the console's element palette, `frontend/apps/console/.../models/elements.ts` |
| Client surface | the `Client surface` tables in the SDK specification |
| Configuration keys | the `Configuration` tables in the SDK specification |
| Operations beyond the specification | the union of every SDK's own client surface, minus the specified operations |

That last axis is the one that catches "the JavaScript SDK grew a method and nobody else
did". The specification names it as the usual origin of a parity gap, so it is scored like
everything else rather than left to memory.

An executor is only scored when it can actually reach a client, which is decided by
whether it emits `USER_INPUT_REQUIRED` or `EXTERNAL_REDIRECTION`, following Go struct
embedding so `GithubOAuthExecutor` inherits the verdict from the OAuth executor it wraps.
The other executors are carried in the report marked *not applicable*, so you can see that
they were considered.

## Theme

The report follows the operating system by default. The masthead carries an Auto / Light /
Dark control that overrides it in either direction, remembered per browser. The choice is
stamped on the page before it paints, so switching does not flash the other theme first, and
a browser that blocks site data simply falls back to the system setting.

## The detail view

Select any row in the report to expand it. A verdict on its own cannot be acted on, so the
detail says what the verdict is made of:

- **What the capability needs.** Each artifact the SDK must have - an input type to render,
  an identifier to submit, an operation to expose - ticked or crossed individually, with the
  `file:line` behind every tick. This is what turns *Partial* into "handles the
  `consent_decisions` submission but renders no `CONSENT_INPUT`".
- **End-to-end coverage, per SDK.** Which tests in that SDK's own suite reference the
  capability, and the term they were matched on. Mobile suites are Maestro flows keyed on
  `thunderid-field-<identifier>`; the JavaScript suite is Playwright.
The server's own integration and end-to-end suites are still measured and carried in
`out/parity.json`, but they are not shown on the page: what a server test covers says
nothing about whether an SDK can drive it, which is the question the page exists to answer.

The `E2E` column on each row is the short version: how many SDK suites reference the
capability at all. Implementation and test coverage are kept as separate claims, because an
SDK can render an input that nothing ever exercises.

## A column is a repository, not a package

Each SDK column covers every package in its repository: JavaScript is eleven, Apple and
Android two each. A cell reads *Missing* only when nothing in any of them has it.

The detail view breaks every part down package by package, so divergence inside one
repository is visible: a capability in react and not in vue is as real a gap as one in
JavaScript and not in Swift. Every package is listed, with the ones carrying the part marked;
the rest are drawn plainly rather than as faults, because not every package is meant to carry
every part and the report does not pretend to know which absences are deliberate.

## Verdicts

| Verdict | Meaning |
|---|---|
| Supported | Evidence found in the SDK's own source, cited as `file:line` |
| Partial | The SDK handles some of what the capability needs and would stall on the rest |
| Missing | The product can emit this and nothing in the SDK handles it |
| Unverified | No detector can decide it. Needs a human, and says so rather than guessing |
| Not applicable | Cannot apply on the platform, with a stated reason, or not an SDK obligation |

Nothing is scored *Supported* without evidence. An unproven pass is worse than an open
question, because it closes a gap nobody then looks at.

## What changed since last week

The dashboard rebuilds every Monday at 06:00 UTC and commits its verdicts to
`snapshots/<date>.json`, so the next run has something to compare against. The parity page
then opens with what moved, in two kinds that are not the same thing:

- **Regressions.** A capability an SDK handled before and does not handle now. This is a
  break, and the run raises a workflow warning for each one.
- **New capabilities already short.** The product grew something and the SDKs have not
  caught up. Expected, and still has to be caught.

Improvements and capabilities no longer discovered are reported quietly below those.

A snapshot holds verdicts only, not evidence, because it is written every week and kept
forever while the file paths behind a verdict churn without the verdict changing. Each is
about 28KB, so a year of them is under two megabytes. Keeping all of them means a comparison
can be made over any span, not only against last week:

```sh
python3 -m parity --baseline snapshots/2026-08-04.json --html out/index.html
```

A regression is a warning rather than a failure: the run still publishes the report that
documents the break. `--fail-on-regression` makes it an error where that is wanted.

## Running it

```sh
pip install -r requirements.txt
python3 -m parity --html out/index.html --json out/parity.json
```

That writes the three pages, the explainer at `how-it-works.html`, and the machine-readable
report. The two live pages go through the `gh` CLI, so they need it installed and logged in;
if a call fails the page says so and a warning goes to the top rather than the section
quietly reading zero.

Point `parity.config.yaml` at your checkouts first. It is the only configuration file, and
the workflow uses the same one with `--sources-root`: a separate CI copy drifted once and
the published report silently showed no end-to-end coverage anywhere until someone noticed. Useful flags:

```sh
python3 -m parity --sources-root src   # every repo under src/, named after its upstream
python3 -m parity --baseline snapshots/latest.json   # report what changed since that run
python3 -m parity --snapshot out/snapshot.json       # record this run's verdicts
python3 -m parity --axis executor      # one axis, as a text table
python3 -m parity --quiet --json -     # machine-readable only
python3 -m parity --fail-on-gap        # non-zero exit when something has no SDK at all
```

## When a new capability appears

Add an executor, an input type, or a row in a specification table, and it turns up on the
next run on its own. The counts above the tables are filters, so each of these is one click
rather than a hunt. Three things want a human:

- **Supported by no SDK.** Either the SDKs have not caught up, or the capability is not
  meant to reach a client. If the latter, the executor should not be emitting a
  client-facing status.
- **No detector yet.** The capability was discovered but nothing can prove an SDK handles
  it, usually because the executor builds its prompt at runtime. Add a detector to
  `catalogue/overrides.yaml`.
- **Stale overrides.** An override names something that no longer exists upstream. Find out
  what replaced it.

## catalogue/overrides.yaml

The only hand-maintained file, and deliberately small. It holds the three judgements
derivation cannot make: an operation an SDK implements under a different name (`aliases`),
a capability that genuinely cannot apply on a platform (`na`, which requires a reason), and
an extra detector for a capability with no wire literal to search for (`detect`). An
override naming a capability that no longer exists is reported rather than ignored, so the
file cannot quietly rot.

## Layout

```
parity/product.py   discovery: what the product can ask for
parity/sdk.py       evidence: what each SDK demonstrably handles
parity/analyze.py   the join, and the verdict rules
parity/report.py    the HTML report
catalogue/          the overrides described above
```
