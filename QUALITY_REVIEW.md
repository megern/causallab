# Independent quality review — causallab v0.2.0

**Status: LOCAL_CANDIDATE_PASS.** Local functional review checkpoint; status depends on current build/security gates and is not an approved published release.

Independent automated QA agent; not a human reviewer. The reviewer did not write or modify production code. This is independent automated review, not human expert validation.

## Observed evidence

- Independently reran the full Python suite: **16 passed**, exit 0. Log: `evidence/rebuild/independent-pytest.txt`.
- Independently reran the Node frontend parsing/conversion/export checks: exit 0. Log: `evidence/rebuild/independent-frontend.txt`.
- Independently probed actual local Docker HTTP on port 18103: health and served guide, current OpenAPI v0.2.0, nonfinite/deep JSON rejection and >2 MiB request rejection passed. Additional application-specific probes are recorded in the portfolio evidence.
- Fresh Docker build/start/HTTP/image scanner evidence was read. No conclusion is drawn from historical v0.1.0 evidence.
- Scope reviewed: Adjusted linear treatment coefficient, HC1 uncertainty and empirical propensity overlap.
- Reviewed the recorded actual browser interactions and screenshots for this tool; the evidence lists the application-specific sample/import/validation/recovery actions that were executed. Fresh v0.2.0 report files were downloaded, parsed independently and replayed against the local API. Scientific reports are paired with separately downloaded analysis inputs. ModelArena real CPU LLM replay validates actual successful calls; generated text and timing are not assumed deterministic.
- Independently checked every served UI asset SHA-256 and every application Python/frontend/guide file inside the running container against reviewed source: all matched exactly. The container image ID matches the image used by the final scanner.
- The final Trivy image gate reported zero MEDIUM/HIGH/CRITICAL findings, including unfixed findings, using the freshly downloaded official vulnerability database. This filtered gate does not establish absence of LOW-severity findings.
- Recorded local Docker image: `sha256:fa9028f7051f3a097db955e5021d51d0805641e7927cdfe0e444d9310eb8b193`. Gate evidence was read from the current root reports. Only the successful gates recorded there are accepted; any pending/failed infrastructure gates are listed below.
- UI source uses text rendering for untrusted data, local assets, bounded import, explicit synthetic provenance, stale-result clearing and export metadata.
- Reviewed source fingerprint (SHA-256 of the sorted per-file source hash map): `dd5dabcecefe79b2d618aa2d4e96d6b273c473a702ed3ff2f8b0a2e8337fb2dc`.

## Findings resolved before acceptance

- Explicit empty CSV records are preserved instead of silently removed; physical blank lines remain ignorable. Regressions cover delimiter-only and quoted-empty records.

## Limits and unresolved work

Observational causal interpretation needs unconfoundedness, positivity and model assumptions. Synthetic recovery does not establish causal validity on enterprise data.

No functional blocker was found in the independent suites and local probes. The following acceptance steps were still pending at this checkpoint:

- current source GitHub CI and version 0.2.0 release provenance.

## Confidence

High for bounded, tested arithmetic, input controls and local HTTP behavior; no general production or scientific external-validity confidence inferred.

Local readiness is limited to documented single-user CPU workflows. Representative private/real-domain data, expert scientific review, production identity controls and deployment-specific load checks are not established by synthetic fixtures. A localhost deployment is the reviewed default.
