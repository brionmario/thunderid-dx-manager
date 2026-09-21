---
name: sdk-parity
description: Generate and triage the ThunderID cross-SDK parity report. Use when asked what is missing from an SDK, whether a flow capability is supported everywhere, what changed since the last report, or to regenerate the parity HTML. Also use after a new executor, input type, flow element, or specification row lands.
---

# ThunderID SDK parity

Answers one question: can every SDK handle everything the product can send it? A flow is
assembled from executors and rendered from elements the server emits. Where an SDK cannot
handle one, an application built on it breaks at that step and nothing earlier says so.

## Generate

```sh
python3 -m parity --html out/index.html --json out/parity.json
```

Add `--axis executor|input|element|surface|config|extra` for one axis as a text table, and
`--quiet` to suppress the text summary. Read `out/parity.json` rather than scraping the
HTML when you need the data.

If a checkout is missing, the run stops and names the path. Fix `parity.config.yaml`; do
not comment an SDK out, because a dropped column reads as "no gaps here".

## Triage, in this order

1. **Supported by no SDK.** The product can emit it and nothing handles it. Decide which:
   the SDKs have not caught up, or the capability was never meant to reach a client. If the
   second, the bug is in the backend emitting a client-facing status, not in the SDKs.
2. **Partial.** More urgent than it looks. The SDK starts the step and stalls partway, so
   it fails in front of a user rather than at build time. The cell's tooltip and the JSON
   `reason` name exactly what is unhandled.
3. **Unverified.** No detector could decide it. Resolve it by reading the executor and
   adding a `detect` entry to `catalogue/overrides.yaml` - never by assuming.
4. **Stale overrides.** An override names a capability that no longer exists upstream.
   Find what replaced it before deleting the entry.

## Reading a verdict

Every `Supported` cites `file:line` in the SDK. Before reporting a gap to someone, open the
evidence for the SDKs that do have it and check the missing one really lacks it rather than
spelling it differently - a different spelling is an `aliases` entry, not a gap.

`Missing` on the *Operations beyond the specification* axis is not automatically a defect.
An operation no SDK was asked for is either something that belongs in the specification and
in all four, or something that should not be public. Say which you think it is.

## Do not

- Do not edit anything under `parity/` to make a specific row come out differently. The
  extractors are general; a wrong row means a wrong detector or a missing override.
- Do not hand-list capabilities anywhere. Everything is discovered from source, which is
  what makes a new executor show up without anyone remembering to add it.
- Do not report a percentage as progress without saying what moved. The denominator changes
  whenever the product grows a capability, so coverage can fall while nothing regressed.

## Filing the gaps

`brion-skills:thunderid-create-dx-task` files these as GitHub issues. One issue per
capability per SDK, naming the flow that breaks and the evidence line, beats one issue
listing forty rows.
