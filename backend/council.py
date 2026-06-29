"""Mode-driven LLM Council orchestration.

Primitives (stages):
  collect    -> N council models answer the query in parallel
  critique   -> N council models critique the provided material (no ranking)
  rank       -> peer review / ranking of anonymized answers (full mode only)
  synthesize -> chairman merges prior outputs (role: "answer" or "review")
  extract    -> single model produces a structured DecisionRecord

Modes compose these primitives (see config.MODES):
  extract: extract
  mini:    collect -> synthesize(answer)
  review:  critique -> synthesize(review)
  full:    collect -> rank -> synthesize(answer)
"""

from typing import List, Dict, Any, Tuple, AsyncGenerator, Optional
from .openrouter import query_models_parallel, query_model
from .config import (
    COUNCIL_MODELS,
    CHAIRMAN_MODEL,
    TITLE_MODEL,
    MODES,
    resolve_mode,
    preset_models,
    resolve_preset,
)
from .decision_memory import extract_decision_record


# --------------------------------------------------------------------------- #
# Stage 1 (collect): individual answers
# --------------------------------------------------------------------------- #

async def stage1_collect_responses(
    user_query: str,
    council_models: List[str] = None,
) -> List[Dict[str, Any]]:
    """Collect individual responses from all council models (in parallel)."""
    council_models = council_models or COUNCIL_MODELS
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(council_models, messages)

    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', ''),
                "usage": response.get('usage'),
            })
    return stage1_results


# --------------------------------------------------------------------------- #
# Critique (review mode): structured critique of provided material, no ranking
# --------------------------------------------------------------------------- #

CRITIQUE_FOCUS = """- Risks
- Weak assumptions
- Security issues
- Cost issues
- Complexity
- Missing constraints
- Better alternatives
- Final recommendation"""


async def stage_critique(
    user_query: str,
    critique_models: List[str] = None,
) -> List[Dict[str, Any]]:
    """Each critique model critiques the provided material along a fixed rubric.

    This is NOT a ranking step. Each model independently critiques the same
    input. The shape matches stage 1 ({model, response}) so the chairman and
    the frontend can reuse the same slot.
    """
    critique_models = critique_models or COUNCIL_MODELS

    critique_prompt = f"""You are an expert reviewer. Critique the following material (which may be code, a plan, an architecture document, a roadmap, a content draft, or a product idea).

Material to review:
{user_query}

Provide a focused, critical review. Do NOT rewrite or replace the material unless a replacement is clearly necessary. Organize your critique under these headings:

{CRITIQUE_FOCUS}

Be specific and concrete. Call out concrete problems rather than vague concerns. If a heading does not apply, say so briefly."""

    messages = [{"role": "user", "content": critique_prompt}]
    responses = await query_models_parallel(critique_models, messages)

    critiques = []
    for model, response in responses.items():
        if response is not None:
            critiques.append({
                "model": model,
                "response": response.get('content', ''),
                "usage": response.get('usage'),
            })
    return critiques


# --------------------------------------------------------------------------- #
# Stage 2 (rank): anonymized peer review (full mode only)
# --------------------------------------------------------------------------- #

async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Each model ranks the anonymized Stage 1 responses."""
    council_models = council_models or COUNCIL_MODELS

    # Anonymized labels: Response A, B, C, ...
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]
    responses = await query_models_parallel(council_models, messages)

    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            # Normalize missing/None content to '' at the boundary so a model
            # that returns no content can't crash the parser or leak "None"
            # into the downstream chairman prompt.
            full_text = response.get('content') or ''
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed,
                "usage": response.get('usage'),
            })

    return stage2_results, label_to_model


# --------------------------------------------------------------------------- #
# Synthesize (chairman): role = "answer" (mini/full) or "review" (review)
# --------------------------------------------------------------------------- #

async def synthesize(
    user_query: str,
    contributions: List[Dict[str, Any]],
    rankings: List[Dict[str, Any]],
    chairman_model: str = None,
    role: str = "answer",
) -> Dict[str, Any]:
    """Chairman merges prior outputs into a single final result.

    role="answer": synthesize the best answer from candidate answers (+ rankings).
    role="review": synthesize a consolidated critique from individual critiques.
    """
    chairman_model = chairman_model or CHAIRMAN_MODEL

    contributions_text = "\n\n".join([
        f"Model: {c['model']}\nResponse: {c['response']}"
        for c in contributions
    ])

    if role == "review":
        chairman_prompt = f"""You are the Chairman of a review council. Multiple expert models have independently critiqued the same material. Synthesize their critiques into a single, consolidated review.

Material that was reviewed:
{user_query}

Individual critiques:
{contributions_text}

Produce one consolidated review. Merge overlapping points, resolve contradictions, and prioritize the most important issues. Do NOT rewrite or replace the material unless clearly necessary. Organize the consolidated review under these headings:

{CRITIQUE_FOCUS}

End with a clear final recommendation."""
    else:
        if rankings:
            rankings_text = "\n\n".join([
                f"Model: {r['model']}\nRanking: {r['ranking']}"
                for r in rankings
            ])
            intro_suffix = ", and then ranked each other's responses"
            rankings_consideration = (
                "The peer rankings and what they reveal about response quality"
            )
        else:
            rankings_text = "(No peer rankings were collected for this mode.)"
            intro_suffix = ""
            rankings_consideration = "The relative strengths of each response"

        chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question{intro_suffix}.

Original Question: {user_query}

Individual Responses:
{contributions_text}

Peer Rankings:
{rankings_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- {rankings_consideration}
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]
    response = await query_model(chairman_model, messages)

    if response is None:
        return {
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis.",
            "usage": None,
        }

    return {
        "model": chairman_model,
        "response": response.get('content', ''),
        "usage": response.get('usage'),
    }


# --------------------------------------------------------------------------- #
# Ranking parsing / aggregation helpers
# --------------------------------------------------------------------------- #

def parse_ranking_from_text(ranking_text: Optional[str]) -> List[str]:
    """Parse the FINAL RANKING section from a model's response.

    Tolerant of a missing/empty ranker output: ``None``, an empty string, or a
    whitespace-only string all yield ``[]`` ("no ranking parsed") rather than
    raising. Unparsable text also yields ``[]`` via the regex fallthrough. This
    keeps `full` mode robust when a council model returns no content.
    """
    import re

    if not ranking_text or not ranking_text.strip():
        return []

    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Compute average rank position for each model across all peer evaluations."""
    from collections import defaultdict

    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = parse_ranking_from_text(ranking['ranking'])
        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_positions[label_to_model[label]].append(position)

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            aggregate.append({
                "model": model,
                "average_rank": round(sum(positions) / len(positions), 2),
                "rankings_count": len(positions)
            })

    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate


# --------------------------------------------------------------------------- #
# Conversation title
# --------------------------------------------------------------------------- #

async def generate_conversation_title(user_query: str) -> str:
    """Generate a short (3-5 word) title from the first user message."""
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]
    response = await query_model(TITLE_MODEL, messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip().strip('"\'')
    if len(title) > 50:
        title = title[:47] + "..."
    return title


# --------------------------------------------------------------------------- #
# Mode-driven orchestration (single source of truth)
# --------------------------------------------------------------------------- #

async def run_mode_stream(
    user_query: str,
    mode: str,
    preset: str,
    persist_extract: bool = True,
) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
    """Run a mode's stage list, yielding (event_type, payload) tuples.

    Payloads are frontend-ready (the SSE layer just adds {'type': event_type}).
    The same generator backs both the streaming and non-streaming endpoints.

    Slot mapping (so the frontend can reuse a small set of components):
      collect / critique -> stage1 events  ({"data": [{model, response}, ...]})
      rank               -> stage2 events  ({"data": [...], "metadata": {...}})
      synthesize         -> stage3 events  ({"data": {model, response}})
      extract            -> extract events ({"data": record, "markdown": str})
    """
    mode = resolve_mode(mode)
    preset = resolve_preset(preset)
    cfg = preset_models(preset)
    council = cfg["council"]
    chairman = cfg["chairman"]
    extract_model = cfg["extract"]

    yield ("start", {"mode": mode, "preset": preset})

    contributions: List[Dict[str, Any]] = []
    rankings: List[Dict[str, Any]] = []

    for stage in MODES[mode]:
        if stage == "collect":
            yield ("stage1_start", {})
            contributions = await stage1_collect_responses(user_query, council)
            yield ("stage1_complete", {"data": contributions})
            if not contributions:
                yield ("error", {"message": "All models failed to respond."})
                return

        elif stage == "critique":
            yield ("stage1_start", {})
            contributions = await stage_critique(user_query, council)
            yield ("stage1_complete", {"data": contributions})
            if not contributions:
                yield ("error", {"message": "All critique models failed to respond."})
                return

        elif stage == "rank":
            yield ("stage2_start", {})
            rankings, label_to_model = await stage2_collect_rankings(
                user_query, contributions, council
            )
            aggregate = calculate_aggregate_rankings(rankings, label_to_model)
            yield ("stage2_complete", {
                "data": rankings,
                "metadata": {
                    "label_to_model": label_to_model,
                    "aggregate_rankings": aggregate,
                },
            })

        elif stage == "synthesize":
            role = "review" if mode == "review" else "answer"
            yield ("stage3_start", {})
            final = await synthesize(user_query, contributions, rankings, chairman, role)
            yield ("stage3_complete", {"data": final})

        elif stage == "extract":
            yield ("extract_start", {})
            record, markdown, usage = await extract_decision_record(
                user_query, extract_model, save=persist_extract
            )
            yield ("extract_complete", {"data": record, "markdown": markdown, "usage": usage})


async def run_full_council(
    user_query: str,
    mode: str = "full",
    preset: str = "balanced",
) -> Tuple[List, List, Dict, Dict]:
    """Non-streaming convenience wrapper. Drains run_mode_stream and assembles
    the legacy 4-tuple (stage1, stage2, stage3, metadata). Decision records and
    mode are folded into metadata for extract mode.
    """
    stage1: List[Dict[str, Any]] = []
    stage2: List[Dict[str, Any]] = []
    stage3: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {"mode": resolve_mode(mode)}

    async for ev_type, payload in run_mode_stream(user_query, mode, preset):
        if ev_type == "stage1_complete":
            stage1 = payload["data"]
        elif ev_type == "stage2_complete":
            stage2 = payload["data"]
            metadata.update(payload["metadata"])
        elif ev_type == "stage3_complete":
            stage3 = payload["data"]
        elif ev_type == "extract_complete":
            metadata["decision_record"] = payload["data"]
            metadata["decision_markdown"] = payload.get("markdown")

    return stage1, stage2, stage3, metadata
