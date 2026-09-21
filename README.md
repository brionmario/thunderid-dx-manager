# thunderid-dx-manager

Tracks what the ThunderID product can ask of an SDK, and whether each SDK answers.

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
- **The product's own suites.** The server's integration and end-to-end tests, scored once.
  A capability the server exercises and no SDK suite does is called out: the behaviour is
  known to work and known to be reachable, and no client drives it.

The `E2E` column on each row is the short version: how many SDK suites reference the
capability at all. Implementation and test coverage are kept as separate claims, because an
SDK can render an input that nothing ever exercises.

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

## Running it

```sh
pip install -r requirements.txt
python3 -m parity --html out/index.html --json out/parity.json
```

Point `parity.config.yaml` at your checkouts first. Useful flags:

```sh
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
