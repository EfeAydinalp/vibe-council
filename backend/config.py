"""Configuration for the LLM Council.

Modes (what stages run) and presets (which models fill the roles) are kept
independent: any mode can be combined with any preset.

Model identifiers are OpenRouter IDs. Some IDs (especially xAI Grok tiers) move
around frequently, so every model below can be overridden via an environment
variable without touching code. See `.env.example` for the full list. If a
default ID 404s on OpenRouter, set the matching env var to a valid ID.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Provider selection (v0.2). Only "openrouter" is supported today; the active
# provider is resolved at call time from the VIBE_PROVIDER env var (default
# below). See backend/providers.py for the selection/validation logic.
DEFAULT_PROVIDER = "openrouter"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Directory for exported decision records (extract mode)
DECISIONS_DIR = "data/decisions"


# --------------------------------------------------------------------------- #
# Model IDs per provider / quality tier.
# Override any of these via environment variables if the OpenRouter ID differs.
# --------------------------------------------------------------------------- #

# Each model is a named, env-overridable slot. Defaults below were verified
# against OpenRouter with a live smoke test (2026-06).
GEMINI_FLASH = os.getenv("MODEL_GEMINI_FLASH", "google/gemini-2.5-flash")
GEMINI_PRO = os.getenv("MODEL_GEMINI_PRO", "google/gemini-2.5-pro")
CLAUDE_HAIKU = os.getenv("MODEL_CLAUDE_HAIKU", "anthropic/claude-haiku-4.5")
CLAUDE_SONNET = os.getenv("MODEL_CLAUDE_SONNET", "anthropic/claude-sonnet-4.5")
CLAUDE_OPUS = os.getenv("MODEL_CLAUDE_OPUS", "anthropic/claude-opus-4.6")
GPT = os.getenv("MODEL_GPT", "openai/gpt-5.1")
# NOTE: x-ai/grok-4 is deprecated on OpenRouter (404 -> use grok-4.3).
GROK = os.getenv("MODEL_GROK", "x-ai/grok-4.3")

# Cheap, fast model used for conversation-title generation.
TITLE_MODEL = os.getenv("MODEL_TITLE", GEMINI_FLASH)

# Maps each model env var to its resolved value, so the CLI can report which IDs
# are in use and whether a value comes from a default or an environment override.
MODEL_ENV_VARS = {
    "MODEL_GEMINI_FLASH": GEMINI_FLASH,
    "MODEL_GEMINI_PRO": GEMINI_PRO,
    "MODEL_CLAUDE_HAIKU": CLAUDE_HAIKU,
    "MODEL_CLAUDE_SONNET": CLAUDE_SONNET,
    "MODEL_CLAUDE_OPUS": CLAUDE_OPUS,
    "MODEL_GPT": GPT,
    "MODEL_GROK": GROK,
    "MODEL_TITLE": TITLE_MODEL,
}


def env_overridden_vars():
    """Return the set of MODEL_* env vars that are currently set (i.e. overriding
    a default). Reads os.environ live; does not expose any secret."""
    return {name for name in MODEL_ENV_VARS if os.getenv(name) is not None}


# --------------------------------------------------------------------------- #
# Presets: which models fill the council / chairman / extract roles.
# Optimized for best quality *within* each cost tier, not globally cheapest.
# --------------------------------------------------------------------------- #

PRESETS = {
    "cheap": {
        "council": [GEMINI_FLASH, CLAUDE_HAIKU],
        "chairman": GEMINI_FLASH,
        "extract": GEMINI_FLASH,
    },
    "balanced": {
        "council": [GPT, CLAUDE_SONNET, GEMINI_PRO],
        "chairman": CLAUDE_SONNET,
        "extract": CLAUDE_SONNET,
    },
    "premium": {
        "council": [GPT, CLAUDE_OPUS, GEMINI_PRO, GROK],
        "chairman": CLAUDE_OPUS,
        "extract": CLAUDE_SONNET,
    },
}


# --------------------------------------------------------------------------- #
# Modes: which stages (primitives) run, in order.
#   collect    -> N models answer the query in parallel
#   critique   -> N models critique the provided material (no ranking)
#   rank       -> peer review / ranking of anonymized answers (full only)
#   synthesize -> chairman merges prior outputs (role depends on mode)
#   extract    -> single model produces a structured DecisionRecord
# --------------------------------------------------------------------------- #

MODES = {
    "extract": ["extract"],
    "mini": ["collect", "synthesize"],
    "review": ["critique", "synthesize"],
    "full": ["collect", "rank", "synthesize"],
}

DEFAULT_MODE = "mini"
DEFAULT_PRESET = "balanced"


def resolve_mode(mode: str) -> str:
    """Return a valid mode, falling back to the default."""
    return mode if mode in MODES else DEFAULT_MODE


def resolve_preset(preset: str) -> str:
    """Return a valid preset name, falling back to the default."""
    return preset if preset in PRESETS else DEFAULT_PRESET


def preset_models(preset: str) -> dict:
    """Return the resolved {council, chairman, extract} models for a preset."""
    return PRESETS[resolve_preset(preset)]


# --------------------------------------------------------------------------- #
# Backward-compatible constants (default preset). Some legacy code/imports and
# the optional non-streaming path still reference these.
# --------------------------------------------------------------------------- #

COUNCIL_MODELS = PRESETS[DEFAULT_PRESET]["council"]
CHAIRMAN_MODEL = PRESETS[DEFAULT_PRESET]["chairman"]
