# Plan: hosted-service strategy (credit-wallet product exploration)

A **strategic product-direction review**, not an implementation plan. `vibe-council
v0.1.0` is published (commit `89ed6d3`), and the [post-v0.1 roadmap](post-v0.1-roadmap.md)
is set: v0.1.1 polish/demo, **v0.2.0 provider abstraction + Ollama**, v0.2.1 experimental
MCP + cost-feedback instrumentation, then later items (Headroom spike, pre-flight cost
estimate, decision search, web UI alignment, packaging).

This document asks a separate, longer-horizon question: **could vibe-council eventually
evolve into a hosted/managed service with accounts and a credit wallet, and if so, what
must land first — without derailing v0.2?** It records the analysis, the risks, a
proposed stance going in, and the one strategic question for the council. **No SaaS,
auth, or billing code is written in this task; no core logic changes; no dependencies
added.**

Review date: **2026-06-28**.

## Current local-first positioning

vibe-council today is a **local-first CLI**:

- The user supplies their **own** `OPENROUTER_API_KEY`; we never hold credentials or
  broker spend. Cost is strictly between the user and OpenRouter.
- All artifacts live in a project-local, gitignored `.council/` workspace
  (`reviews/`, `diffs/`, `decisions/`, `stages/`, `usage/`, …). Nothing leaves the
  machine except the model calls the user explicitly triggers.
- The only network egress is to OpenRouter, and that is documented in the privacy/
  local-first notes.
- Guardrails (premium/token/cost/loop/key guards) exist to contain *the user's own*
  spend and footguns — not to meter a balance we sell.

This posture is the project's credibility anchor: it is safe to embed in agents, leaks
no key, retains no user data server-side, and has **no operational liability** because
we run no server. The "moat" identified in the roadmap is the honest, scriptable,
agent-friendly CLI surface — not a hosted backend.

## The hosted service idea

The proposal is a website / managed service where:

- users create an **account**;
- users **buy credits / balance** from our site;
- users run council reviews through **our hosted** service (we hold the provider key and
  pay the model bill, drawing down their credit balance);
- we may ship **project files / templates / workflows** (curated review presets,
  decision-record formats, starter `.council/` configs);
- we may **integrate with Claude Code / agents** so users can trigger council workflows
  automatically (e.g. via MCP or a hosted API);
- the **local-first CLI remains available**, but a hosted/business layer sits alongside
  it.

In short: a transition from "tool you run with your own key" to "service you pay us to
run for you," with a prepaid wallet as the monetization primitive.

## Possible value proposition

What a hosted layer could genuinely offer over the local CLI:

1. **Zero-setup.** No clone, no venv, no OpenRouter signup, no key handling. Sign in,
   buy credits, run. This is the single biggest friction removal for non-developers.
2. **Aggregated/curated model access.** We pick and maintain the council/chairman model
   roster; users don't track model IDs or pricing churn.
3. **Hosted decision memory.** Searchable, cross-device, team-shareable decision records
   instead of a local `.council/` folder.
4. **Team / collaboration surface.** Shared workspaces, review history, org-level
   billing — things a local CLI structurally cannot offer.
5. **Agent-native trigger point.** A hosted endpoint/MCP that an agent (Claude Code,
   CI bot) can call without the human provisioning a key first.
6. **Curated workflows/templates** as a product layer — opinionated review recipes that
   encode best practice.

The honest counterpoint: items 1–2 are conveniences a determined developer doesn't need,
and items 3–6 are real but require us to become a *data custodian* and *spend broker* —
which is exactly where the risk lives.

## Who would pay, and why

| Segment | Why they'd pay | Strength of pull |
|---------|----------------|------------------|
| Non-technical / light users | Avoid setup + key management entirely | Real, but small wallets; price-sensitive |
| Teams / orgs | Shared decision memory, org billing, audit trail | Strongest willingness to pay; needs SSO/compliance |
| Agent/CI builders | A callable hosted endpoint with no per-user key provisioning | Real, but they can self-host the CLI cheaply |
| Existing CLI power users | Little — they already have keys and local artifacts | Weak; not the buyer |

The paying buyer is most plausibly **teams**, not individuals — and teams are the
segment with the *highest* security, compliance, and data-handling expectations, which
raises the bar on everything below.

## What changes technically

Moving from CLI to hosted service is not an increment; it is a different product class:

- **We hold the provider key** and pay the model bill, then reconcile against credits.
  Today the user's key is the spend boundary; hosted erases that boundary and puts us on
  the hook for every token.
- **Multi-tenant backend** — accounts, sessions, isolation between users' data and
  workspaces. The current `.council/` model is single-user, single-machine.
- **Metering & accounting** — per-request token/cost accounting that is *authoritative*
  (it debits real money), not the current best-effort `--usage` display.
- **Provider abstraction becomes load-bearing** — to control cost and avoid single-
  provider lock-in for a business, the v0.2.0 abstraction is now a hard prerequisite, not
  a nicety.
- **Rate limiting / quotas / queueing** — to bound our exposure to runaway or abusive
  usage.
- **Hosted API + auth surface** (and likely the MCP server) become the primary interface,
  raising concurrency/timeout/retry demands on the core well beyond CLI needs.
- **Observability** — logging, billing reconciliation, fraud signals, incident tooling.

Most of this is *new* surface area, much of it security-sensitive, none of it on the
current v0.2 path.

## What changes legally / security-wise

- **We become a money-handling business.** Selling prepaid credits implicates payment
  processing (PCI via Stripe et al.), possibly stored-value/prepaid regulations, sales
  tax/VAT, refunds, and chargebacks.
- **We become a data processor.** User prompts (often containing proprietary code) now
  transit and may be stored on our infrastructure → GDPR/CCPA obligations, a real privacy
  policy, ToS, DPA for teams, breach-notification duties.
- **Provider ToS pass-through.** We must ensure our usage of OpenRouter/model providers
  permits reselling inference, and propagate their content/use restrictions to our users.
- **Liability surface.** Outages, double-billing, lost decision records, and leaked
  prompts are now *our* incidents, with reputational and possibly legal cost.
- **Security review bar rises sharply** — authn/authz, tenant isolation, secret
  management (our provider key is now a high-value target), and abuse handling all need
  real review, not the lightweight posture a local CLI can afford.

## Billing / credit risk

- **Float & reconciliation.** Prepaid credit is a liability on our books until consumed;
  we must reconcile credits-sold against model-cost-incurred continuously or bleed money.
- **Pricing model risk.** If model prices move (they do, often), a fixed credit price can
  invert margins overnight. Need a cost-plus or buffered margin and the ability to reprice.
- **Refunds/disputes/chargebacks.** Prepaid balances invite "I didn't use these / it
  didn't work" disputes; chargebacks carry fees and fraud-score penalties.
- **Unit-economics opacity.** A single `full` run fans out to many models; without a
  *pre-flight estimate* we can't quote a price or debit fairly, and users can't predict
  cost. Pre-flight estimate (a "later" roadmap item) becomes a prerequisite.

## Model cost risk

- **We absorb variance.** Long inputs, expensive chairman models, and `full`'s multi-
  model fan-out mean per-request cost swings widely. We eat the gap between credits
  charged and tokens burned.
- **No hard ceiling today.** The cost guard is best-effort and advisory; a hosted service
  needs *enforced* per-request and per-account ceilings before a single user can hand us a
  surprise bill.
- **Provider outages/price changes** hit our margin and SLA directly, not the user's.

## Abuse / rate-limit risk

- **Free-tier / signup abuse.** Any trial credit invites automated signups farming free
  inference. Needs identity friction, rate caps, and anomaly detection from day one.
- **Resource exhaustion.** Large files / repeated `full` runs can be used to burn our
  provider quota or rack cost. Needs enforced quotas, per-account concurrency limits, and
  input-size caps.
- **Prompt-content abuse.** Users may submit content that violates provider use policies;
  we inherit responsibility for moderation/pass-through enforcement.
- The current loop guard is a *footgun* guard for one well-meaning user — not an
  adversarial rate limiter.

## Privacy / data-retention risk

- **Prompts contain secrets.** Code review inputs routinely include proprietary source,
  credentials, and IP. Hosting them server-side makes us a high-value breach target and a
  custodian of others' secrets.
- **Retention policy required.** We'd need an explicit, defensible retention/deletion
  policy (and the engineering to honor deletion), plus clarity on whether prompts are ever
  used for anything beyond serving the request.
- **This directly contradicts the current privacy promise** ("artifacts stay in
  `.council/`; nothing leaves except the model call you trigger"). A hosted layer must be
  *clearly separated* so the local-first promise isn't quietly broken for CLI users.

## Does this conflict with local-first open-source identity?

Partially, and the conflict must be managed explicitly rather than papered over:

- **Identity tension.** The project's trust comes from "your key, your machine, no server,
  no data custody." A paid hosted layer is the opposite stance. If conflated, it erodes the
  exact credibility that drives current adoption.
- **Manageable if cleanly separated.** "Open-source local-first CLI" and "optional hosted
  convenience for those who want it" can coexist (cf. many OSS-core + hosted businesses) —
  **but only if** the local path stays first-class, fully functional, key-in-your-own-
  hands, and never degraded to upsell the hosted tier.
- **Failure mode to avoid:** hosted-first decisions leaking into the core (telemetry,
  forced accounts, crippled local mode). That would convert a credibility asset into a
  liability.

## Should this affect v0.2 priorities?

**Proposed answer: no — v0.2 should not change.** But the analysis sharpens *why* the
existing v0.2 sequence is correct regardless of whether hosting ever happens:

- **Provider abstraction (v0.2.0)** is a no-regret investment: it's already the top
  roadmap item *and* it is the hard prerequisite for any hosted cost control. Building it
  for its own sake also de-risks the hosted option for free.
- **Cost-feedback instrumentation (v0.2.1)** likewise feeds both the CLI's `--usage`
  honesty and any future metering/pre-flight-estimate need.
- **MCP (v0.2.1, experimental)** is the natural agent-trigger interface a hosted layer
  would later expose — again, no-regret.

So the hosted idea should **reinforce, not reorder** v0.2. The danger is letting hosted
ambitions pull auth/billing/multi-tenant work *forward* into v0.2 and starve the provider-
abstraction work that everything (including hosting) depends on.

## Proposed stance (before council)

1. **Do not build a hosted SaaS now.** It is a different product class with money-handling,
   data-custody, and security obligations the project is not resourced to take on at v0.2.
2. **Keep v0.2 focused** on provider abstraction + Ollama (v0.2.0) and experimental MCP +
   cost-feedback instrumentation (v0.2.1), exactly as the post-v0.1 roadmap states.
3. **Treat the hosted service as a future, optional product exploration** — explicitly
   downstream of v0.2, never a reason to reorder it.
4. **Preserve local-first as the primary identity.** Any future hosted layer must sit
   *alongside* a first-class, undegraded local CLI, not replace or subsidize itself by
   weakening it.
5. **If the hosted service remains interesting, these prerequisites must land first**
   (most are already on the roadmap or fall out of it):
   - **provider abstraction** (v0.2.0) — cost control + no single-provider business lock-in;
   - **cost accounting** — authoritative, enforced per-request/per-account metering
     (beyond today's best-effort `--usage`);
   - **pre-flight cost estimates** — so spend can be quoted and debited fairly;
   - **auth / billing** — accounts, payment processing, prepaid-credit ledger;
   - **abuse prevention** — enforced quotas, rate limits, signup-abuse defenses;
   - **data-privacy policy** — retention/deletion, ToS, DPA, provider-ToS pass-through;
   - **stronger security review** — multi-tenant isolation, secret management, authz;
   - **MCP / agent-interface stability** — the agent trigger point must be solid before
     it's the paid surface.

Net: the cheapest, highest-leverage hosted prerequisites (provider abstraction, cost
accounting, pre-flight estimate, MCP) are *already* the v0.2/later roadmap. The
expensive, identity-risky parts (auth, billing, multi-tenant, data custody) are
explicitly **out of scope until a real demand signal justifies them.**

## Main strategic question

> **Should vibe-council remain local-first through v0.2, or should we start preparing for
> a hosted credit-based service? If hosted is plausible, what prerequisites must land
> before it is safe to pursue?**

Sub-questions for the council:

- Is "do not build hosted now; keep v0.2 unchanged; treat hosting as downstream optional"
  the right call, or is there a first-mover reason to start hosted scaffolding sooner?
- Does a **prepaid credit wallet** make sense for this product, or is a different model
  (BYO-key + flat subscription, usage pass-through, none) better?
- Which hosted prerequisite is most **underestimated** in cost/risk?
- Can local-first and hosted genuinely coexist, or does adding a paid hosted layer
  inevitably corrode the local-first/open-source identity?
- Are we **wrong** anywhere — e.g. is the team/buyer thesis or the "v0.2 unchanged"
  conclusion mistaken?

## Council guidance summary

`full --preset balanced` failed on a transient model/parse error (a council model
returned empty content, which the ranking parser doesn't tolerate), so per policy the
review ran via `review --preset balanced` (2026-06-28). Output is advice to filter, not
authority — the section below is the **human-curated** reading, not a verbatim apply. Raw
output stayed in the gitignored `.council/`.

### Should the hosted service affect v0.2 or not?
**No.** The council was emphatic: keep v0.2 exactly as planned — provider abstraction +
Ollama (v0.2.0), experimental MCP + cost-feedback instrumentation (v0.2.1) — with zero
deviation. These are no-regret investments that de-risk *both* the CLI and any future
monetization. The danger is letting hosted ambitions reorder or starve them; that danger
is real and we should explicitly guard against it.

### Strongest argument *for* hosted
Zero-setup access to a curated council, and — more durably — a **team / collaboration +
shared decision-memory** surface that a local single-machine CLI structurally cannot
offer. That team value is the only segment with credible willingness to pay. Note the
council reframed even this: the value is *collaboration/governance*, capturable **without**
becoming an inference reseller (see BYOK below).

### Strongest argument *against* hosted
It is a **pivot to a different company**, not a feature. The council's hardest points:
(1) it irreversibly dilutes the local-first trust anchor the moment it exists ("which
version is this, is my code being sent somewhere?"); (2) a prepaid credit wallet drags us
into money-transmitter/escheatment/PSD2 territory and chargeback/float risk; (3) reselling
inference likely violates provider ToS without negotiated commercial terms (a go/no-go
gate, not a checkbox); (4) 12–18 months and ~$200k–$500k to reach a buyer that then
demands another 6–12 months of enterprise features. Risk/reward is inverted.

### Minimum prerequisites before hosted (if ever pursued)
Beyond the doc's original list, the council added hard *gates*:
- **provider abstraction** (already v0.2.0) — cost control, no single-provider lock-in;
- **authoritative, enforced cost accounting** + **pre-flight cost estimates** — these are
  a **launch blocker, not a "later" item**: you cannot sell credits for an unpriced product;
- a **worst-case per-request cost model** proving **positive, durable unit economics**
  before any build;
- **provider-ToS commercial terms** negotiated/signed (go/no-go);
- **legal scoping** of money-transmitter / escheatment / PSD2 + ToS/Privacy/DPA review;
- **third-party security audit**, a **designed** multi-tenant isolation + threat model,
  and secret management for the now-centralized provider key;
- **abuse prevention** (signup-farming defenses, enforced quotas, input caps, moderation);
- **MCP / agent-interface stability** *if* it's the trigger surface (council flagged MCP
  as unvalidated/experimental — don't anchor a paid surface to it prematurely).

### Biggest security / legal / product risks
- **Security:** master provider key becomes a single high-value target (one breach drains
  all balances); multi-tenant isolation is named but not designed; stored prompts carry
  breach-notification duties; adversarial token-burn becomes *our* bill.
- **Legal:** prepaid stored-value regulation (MSB licensing, escheatment, PSD2); reselling
  inference vs. provider ToS; data-processor (GDPR/CCPA) obligations; chargeback ratios
  that can get payment processing terminated.
- **Product:** **identity dilution** — even *signaling* a hosted pivot invites hostile
  forks ("the one that stayed local-first") and erodes the moat; "we won't degrade the
  CLI" is wishful without a binding governance lock.

### Does a credit wallet make sense?
**No — shelve it.** The council called the prepaid wallet the *worst* of the options:
highest regulatory, float-accounting, refund/chargeback, and abuse exposure, with the
least upside. If any paid hosted experiment is ever run, prefer **pay-per-run Stripe
Checkout with hard caps** (stays out of stored-value land) over a generic wallet.

### Should local-first identity remain primary?
**Yes — unequivocally, and it should be made *binding*, not just promised.** The council
recommended a permanent **local-first parity lock** (core logic must run without auth or
network beyond the user's own LLM provider) and a **governance/licensing lock** (e.g.
Apache-2.0/AGPL + contributor agreement) so the promise can't be quietly walked back under
revenue pressure.

### Recommended next 3 roadmap actions
1. **Ship v0.2 unchanged.** Provider abstraction + Ollama (v0.2.0), then experimental MCP
   + cost-feedback instrumentation (v0.2.1). Hosted does not reorder this.
2. **Reframe monetization away from a credit wallet toward BYOK + subscription** as the
   *primary* (cheap, low-risk, trust-preserving) validation path — users keep their own
   key/spend; we charge for collaboration, shared decision memory, SSO, CI integration.
   Treat **self-hosted enterprise edition** as the secondary path. Both honor local-first.
3. **Write down hard go/no-go constraints before any hosted work:** a measurable demand
   threshold (e.g. N credible team requests) + a capped validation budget; positive unit
   economics; legal + third-party security sign-off; and the local-first parity +
   governance locks above. Absent the signal, hosted stays permanently tabled.

### Where I diverge from the council (curated, not blindly applied)
- **Adopt** the headline (don't build hosted; keep v0.2; wallet is the wrong primitive)
  and the BYOK-subscription reframe — it captures the team value the doc identified
  without the data-custody/spend-broker liability.
- **Treat the cost figures as directional, not estimates.** "$200k–$500k / 12–18 months"
  is a useful order-of-magnitude warning, not a costed plan; it reinforces "not now"
  rather than setting a budget.
- **Note the council's own framing nudge:** it argued the strategic question is a false
  binary and should be "what monetization, if any, preserves local-first and has validated
  demand?" That's fair — but the original binary is still the decision *this* doc needed to
  settle, and the answer ("remain local-first through v0.2") stands.

## Constraints

- Strategy/planning only. **No** SaaS, auth, billing, or multi-tenant code; no core logic
  changes; no new dependencies in this task.
- Council runs use the **`balanced`** preset only (no premium), always with `--usage`.
- `full --preset balanced` is the primary run; `review --preset balanced` only if `full`
  fails.
- Raw `.council/` outputs stay local and are **never** committed.
- No commit, push, or PR without explicit approval.
