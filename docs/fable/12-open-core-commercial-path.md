# 12 — Open-core / commercial path

## Principle

**Do not hide the whole repo.** The moat is **trust**: an auditable, deterministic guard you can read
is the entire pitch. Closing the core kills the reason to trust it. Open-core, not closed-with-a-demo.

## Keep open (public core)

These **must** stay inspectable, or the "deterministic guard you can audit" claim collapses:

- the `vibe` CLI
- the local Workbench (panel, runtime, orchestrator)
- the **deterministic trust boundary**
- the **guarded executor**
- the read-only **MCP** surface
- local **context / memory** (decisions, context pack, redaction guard)
- the **agent bridge basics** (proposal schema + importer)

## Plausibly paid / hosted later

Convenience and team/enterprise features built *on top of* the open core — not replacements for it:

- managed **team dashboard**
- **mobile approvals** (a hosted transport for the v0.8 approval path)
- **shared / immutable audit logs**
- **org policy packs** (shareable, tighten-only trust configs)
- **managed integrations**
- **council packs / templates**
- **BYOK usage dashboard**
- **support / training**

## Risks of monetizing too early

1. **License / provenance "Question 0" is unresolved.** vibe-council descends from an unlicensed
   upstream (`karpathy/llm-council`). You **cannot** sell, or offer a commercial grant on, a codebase
   whose upstream license is unsettled. This is a hard **blocker** for any paid tier — a legal task,
   not an engineering one, and it must be resolved first. Do not add a `LICENSE` unilaterally.
2. **Selling before adoption** — a hosted tier over a product nobody uses is convenience for an empty
   room. Adoption of the open core comes first.
3. **Local-first messaging risk** — a hosted tier that touches the audit log or approvals sits in
   tension with "local-first." The messaging must be precise: the hosted layer is an **optional**
   add-on; the local product remains fully functional and local without it.

## Recommendation / sequencing

- Resolve Question 0 **in parallel** (legal), independent of the roadmap.
- Keep **everything open through v0.7**.
- Do **not** build any paid surface or hosted infrastructure until the open core has real adoption and
  Question 0 is cleared.
- When a hosted layer does start (v0.9+), it is **full**-review and needs non-engineering (legal /
  business) sign-off, not just a code review.

## Non-goals (now)

- No hiding the repo. No closing the core. No hosted infra. No commercial/pricing claim. No `LICENSE`
  change. No removal/weakening of upstream attribution.
