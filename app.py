"""
JewelBench — Bulk Jewelry Variation Generator (Streamlit)
==========================================================
Uses ONLY Fal.ai (single API key):
  - Florence-2 Large → captioning + type detection + stone count detection
  - Flux 2 Turbo Edit → single-component image editing

All prompts use JEWELRY_CONTEXT scene frame to prevent literal
interpretations (e.g. Flux reads "cathedral" in jewelry context,
not as a building). Scene framing > role assignment for image models.

RUN:  pip install streamlit fal-client Pillow requests
"""

import streamlit as st
import os
import json
import random
import time
import requests

st.set_page_config(
    page_title="JewelBench — Bulk Variations",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS
# ============================================================================
st.markdown("""
<style>
    .stApp, .main, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #1a1a1a !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        color: #1a1a1a !important;
    }
    section[data-testid="stSidebar"] * {
        color: #1a1a1a !important;
    }
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stText, label,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span {
        color: #1a1a1a !important;
    }
    .stCheckbox label p, .stCheckbox label span,
    [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] label span,
    [data-testid="stCheckbox"] label div {
        color: #1a1a1a !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    .stSelectbox div[data-baseweb="select"] span {
        color: #1a1a1a !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
    }
    .main-header {
        background: linear-gradient(135deg, #1B3A5C 0%, #2E75B6 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .main-header h1 {
        color: #FFFFFF !important;
        font-size: 28px !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    .main-header p {
        color: rgba(255,255,255,0.85) !important;
        font-size: 14px !important;
        margin: 4px 0 0 0 !important;
    }
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #1B3A5C !important;
        margin: 0 0 4px 0;
    }
    .section-sub {
        font-size: 13px;
        color: #4a5568 !important;
        margin: 0 0 16px 0;
    }
    .detect-box {
        background: #F0F7FF;
        border: 2px solid #2E75B6;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 16px 0;
    }
    .detect-type {
        font-size: 22px;
        font-weight: 700;
        color: #1B3A5C !important;
        text-transform: capitalize;
    }
    .detect-caption {
        font-size: 13px;
        color: #4a5568 !important;
        margin-top: 8px;
        line-height: 1.5;
        font-style: italic;
    }
    .stone-counts {
        background: #FFF7ED;
        border: 1px solid #FDBA74;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: #9A3412 !important;
    }
    .blue-divider {
        height: 3px;
        background: linear-gradient(90deg, #2E75B6, transparent);
        border: none;
        border-radius: 2px;
        margin: 24px 0;
    }
    .stProgress > div > div > div > div {
        background-color: #2E75B6;
    }
    #MainMenu, footer, header {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# JEWELRY CONTEXT
# ============================================================================
JEWELRY_CONTEXT = (
    "Professional jewelry product photo, close-up studio shot. "
    "All edits are jewelry metalwork modifications only. "
    "No real objects, no buildings, no animals, no overlays. "
    "Single seamless manufactured piece, not a composite. "
)


# ============================================================================
# STONE SYSTEM
# ============================================================================
DIAMOND_MAIN = {
    "setting": [
        "4-prong claw", "6-prong claw", "full bezel", "half bezel",
        "tension set", "cathedral bezel", "collet set", "gypsy/flush set",
    ],
    "shape": [
        "round brilliant", "princess cut", "oval", "emerald cut",
        "cushion", "pear", "marquise", "radiant", "asscher", "heart",
    ],
    "style": [
        "solitaire", "halo", "double halo", "three-stone center",
        "cluster", "bezel solitaire", "tension solitaire",
    ],
    "prong": [
        "round prong", "pointed/claw prong", "V-prong", "double prong",
        "tab prong", "button prong", "tulip prong",
    ],
}

DIAMOND_SIDE = {
    "setting": [
        "channel set", "pave set", "bezel set", "bar set",
        "invisible set", "U-cut pave",
    ],
    "shape": [
        "round brilliant", "baguette", "tapered baguette",
        "princess cut", "trillion",
    ],
    "style": [
        "pave band", "channel row", "eternity set", "half-eternity",
        "three-stone side pair", "graduated row",
    ],
    "prong": [
        "shared prong", "fish-tail set", "bright-cut pave",
        "U-cut", "scalloped set",
    ],
}

DIAMOND_ACCENT = {
    "setting": [
        "micro pave", "channel set", "flush/gypsy set",
        "bar set", "bead set", "burnish set",
    ],
    "shape": [
        "round brilliant", "single-cut round", "baguette",
        "marquise", "french cut",
    ],
    "style": [
        "scattered accent", "pave trail", "milgrain-set cluster",
        "flush scattered", "halo ring",
    ],
    "prong": [
        "bead set (no prong)", "micro-prong", "shared prong", "bright-cut",
    ],
}

COLORED_GEMSTONES = [
    "ruby", "blue sapphire", "emerald", "aquamarine", "amethyst",
    "topaz", "garnet", "peridot", "opal", "alexandrite",
]
COLORED_SIDE_GEMS = [
    "ruby", "blue sapphire", "emerald", "pink sapphire", "amethyst",
]
COLORED_ACCENT_GEMS = [
    "ruby", "blue sapphire", "emerald", "pink sapphire", "amethyst",
]

COLORED_MAIN = {
    "setting": [
        "4-prong claw", "6-prong claw", "full bezel", "half bezel",
        "tension set", "cathedral bezel", "collet set", "gypsy/flush set",
    ],
    "shape": [
        "oval", "emerald cut", "cushion", "pear", "round brilliant",
        "cabochon", "marquise", "trillion", "sugarloaf cabochon",
    ],
    "style": [
        "solitaire", "halo", "double halo", "three-stone center",
        "cluster", "bezel solitaire",
    ],
    "prong": [
        "round prong", "pointed/claw prong", "V-prong",
        "double prong", "tab prong", "button prong",
    ],
    "gemstone": COLORED_GEMSTONES,
}

COLORED_SIDE = {
    "setting": [
        "channel set", "pave set", "bezel set", "bar set",
        "invisible set", "U-cut pave",
    ],
    "shape": [
        "round", "baguette", "tapered baguette", "princess cut",
        "trillion", "oval",
    ],
    "style": [
        "pave band", "channel row", "eternity set", "half-eternity",
        "three-stone side pair", "graduated row", "alternating color",
    ],
    "prong": [
        "shared prong", "fish-tail set", "bright-cut pave",
        "U-cut", "scalloped set",
    ],
    "gemstone": COLORED_SIDE_GEMS,
}

COLORED_ACCENT = {
    "setting": [
        "micro pave", "channel set", "flush/gypsy set",
        "bar set", "bead set", "burnish set",
    ],
    "shape": [
        "round", "baguette", "marquise", "french cut", "princess cut",
    ],
    "style": [
        "scattered accent", "pave trail", "milgrain-set cluster",
        "flush scattered", "halo ring",
    ],
    "prong": [
        "bead set (no prong)", "micro-prong", "shared prong", "bright-cut",
    ],
    "gemstone": COLORED_ACCENT_GEMS,
}

STONE_CATEGORIES = {
    "diamond_main":   {"label": "💎 Diamond — Main Stone",    "data": DIAMOND_MAIN,   "type": "diamond",  "position": "main"},
    "diamond_side":   {"label": "💎 Diamond — Side Stones",   "data": DIAMOND_SIDE,   "type": "diamond",  "position": "side"},
    "diamond_accent": {"label": "💎 Diamond — Accent Stones", "data": DIAMOND_ACCENT, "type": "diamond",  "position": "accent"},
    "colored_main":   {"label": "🔴 Colored — Main Stone",    "data": COLORED_MAIN,   "type": "colored",  "position": "main"},
    "colored_side":   {"label": "🔵 Colored — Side Stones",   "data": COLORED_SIDE,   "type": "colored",  "position": "side"},
    "colored_accent": {"label": "🟢 Colored — Accent Stones", "data": COLORED_ACCENT, "type": "colored",  "position": "accent"},
}


# ============================================================================
# 4 UNIVERSAL PARAMS
# ============================================================================
UNIVERSAL_STYLES = [
    "Neo-Heritage Vintage",
    "Indo-Western Art Deco",
    "East-West Minimalist",
    "Contemporary Geometric",
    "Navratna Modern Classic",
    "Nature-Inspired Modern",
    "Minimalist",
    "Classic",
]

UNIVERSAL_METAL_TYPE = [
    "18K yellow gold", "18K white gold", "18K rose gold",
    "platinum", "sterling silver",
]

UNIVERSAL_METAL_FINISH = [
    "high polish", "brushed matte", "satin", "hammered",
]

UNIVERSAL_DETAILING = [
    "milgrain border", "filigree side panels", "hand engraving",
    "rope edge", "knife edge", "scrollwork", "vine engraving",
    "geometric etching", "diamond-cut faceting",
]


# ============================================================================
# NON-STONE PARAMS PER TYPE
# ============================================================================

TYPE_ICONS = {
    "ring": "💍", "pendant": "📿", "earring": "✨", "bangle": "⭕",
    "necklace": "📿", "bracelet": "⛓️", "statue": "🗿",
}
VALID_TYPES = ["ring", "pendant", "earring", "bangle", "necklace", "bracelet", "statue"]

NON_STONE_PARAMS = {
    "ring": {
        "style":          {"label": "Style",          "values": UNIVERSAL_STYLES},
        "shank_style":    {"label": "Shank style",    "values": ["knife-edge", "tapered", "comfort-fit rounded", "flat band", "euro-shank", "split-shank", "twisted rope", "bypass-swirl", "open lattice", "cathedral shank", "double-rail", "architectural ribbed"]},
        "head_type":      {"label": "Head type",      "values": ["basket mount", "cathedral", "bezel frame", "low-profile flush", "crown head", "suspended crown", "tension bridge", "geometric frame", "double halo head", "raised pedestal", "split-claw head"]},
        "metal_type":     {"label": "Metal type",     "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":   {"label": "Metal finish",   "values": UNIVERSAL_METAL_FINISH},
        "shoulder_style": {"label": "Shoulder style", "values": ["plain", "pave-set", "tapered baguette", "milgrain edged"]},
        "gallery_style":  {"label": "Gallery",        "values": ["open gallery", "closed gallery", "filigree gallery", "hidden halo gallery", "pierced gallery", "lattice gallery"]},
        "detailing":      {"label": "Detailing",      "values": UNIVERSAL_DETAILING},
    },
    "pendant": {
        "style":         {"label": "Style",         "values": UNIVERSAL_STYLES},
        "pendant_shape": {"label": "Pendant shape", "values": ["round", "oval", "teardrop", "heart", "bar", "disc", "geometric hexagon", "marquise silhouette", "cross", "star", "crescent moon", "kite/rhombus", "shield", "octagon"]},
        "frame_style":   {"label": "Frame style",   "values": ["open frame", "closed back", "halo frame", "minimal wire frame", "double frame", "vintage scroll frame", "art deco geometric frame", "floating/tension frame", "cage/lantern frame", "bezel wrap frame"]},
        "bail_type":     {"label": "Bail type",     "values": ["fixed bail", "hidden bail", "tube bail", "diamond-set bail", "split bail", "double loop bail"]},
        "metal_type":    {"label": "Metal type",    "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":  {"label": "Metal finish",  "values": UNIVERSAL_METAL_FINISH},
        "detailing":     {"label": "Detailing",     "values": UNIVERSAL_DETAILING},
    },
    "earring": {
        "style":            {"label": "Style",        "values": UNIVERSAL_STYLES},
        "earring_type":     {"label": "Earring type", "values": ["stud", "drop", "hoop", "huggie", "chandelier", "climber", "threader", "ear cuff", "jacket", "dangle", "crawler", "front-back (peek-a-boo)", "shield/disc"]},
        "silhouette_shape": {"label": "Silhouette",   "values": ["round", "oval", "teardrop", "geometric angular", "linear bar", "fan/semicircle", "floral cluster", "abstract organic", "kite/diamond", "starburst", "crescent", "triangular", "cascading tier"]},
        "closure_type":     {"label": "Closure type", "values": ["push back", "screw back", "lever back", "hook/shepherd", "hinged", "latch back", "snap post", "omega clip", "threader chain", "ear wire with bead stop"]},
        "frame_style":      {"label": "Frame style",  "values": ["open", "closed", "filigree", "sculpted solid", "cage/lantern", "lattice", "halo surround", "art deco geometric", "floating/tension"]},
        "metal_type":       {"label": "Metal type",   "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":     {"label": "Metal finish", "values": UNIVERSAL_METAL_FINISH},
        "drop_length":      {"label": "Drop length",  "values": ["flush to ear (stud)", "short drop (1-2cm)", "medium drop (3-4cm)", "long drop (5-7cm)"]},
        "detailing":        {"label": "Detailing",    "values": UNIVERSAL_DETAILING},
    },
    "bangle": {
        "style":        {"label": "Style",           "values": UNIVERSAL_STYLES},
        "bangle_type":  {"label": "Bangle type",     "values": ["solid closed", "hinged", "open cuff", "coil wrap", "stacking thin", "bypass cuff", "expandable", "mesh flex", "articulated segment"]},
        "closure_type": {"label": "Closure type",    "values": ["slip-on (no clasp)", "hinged with clasp", "box clasp", "magnetic clasp", "toggle clasp", "hook and eye", "push-pull clasp", "barrel screw", "fold-over safety"]},
        "band_width":   {"label": "Band width",      "values": ["slim (3mm)", "medium (6mm)", "wide (10mm)", "extra wide (15mm)"]},
        "metal_type":   {"label": "Metal type",      "values": UNIVERSAL_METAL_TYPE},
        "metal_finish": {"label": "Metal finish",    "values": UNIVERSAL_METAL_FINISH},
        "detailing":    {"label": "Detailing",       "values": UNIVERSAL_DETAILING},
    },
    "necklace": {
        "style":         {"label": "Style",          "values": UNIVERSAL_STYLES},
        "necklace_type": {"label": "Necklace type",  "values": ["chain", "pendant chain", "choker", "station necklace", "lariat/Y-chain", "collar", "multi-strand"]},
        "chain_style":   {"label": "Chain style",    "values": ["cable link", "box chain", "curb link", "rope chain", "figaro", "snake chain", "Singapore twist"]},
        "link_shape":    {"label": "Link shape",     "values": ["round", "oval", "elongated rectangle", "flat disc", "N/A (solid chain)", "twisted figure-8", "marquise link", "heart link"]},
        "metal_type":    {"label": "Metal type",     "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":  {"label": "Metal finish",   "values": UNIVERSAL_METAL_FINISH},
        "clasp_type":    {"label": "Clasp type",     "values": ["lobster claw", "spring ring", "toggle", "box clasp", "magnetic"]},
        "detailing":     {"label": "Detailing",      "values": UNIVERSAL_DETAILING},
    },
    "bracelet": {
        "style":         {"label": "Style",          "values": UNIVERSAL_STYLES},
        "bracelet_type": {"label": "Bracelet type",  "values": ["chain link", "tennis", "cuff", "charm", "bar/ID", "mesh", "bangle style", "wrap", "beaded", "hinged segment"]},
        "link_style":    {"label": "Link style",     "values": ["cable", "curb", "figaro", "rope", "box", "N/A (solid)", "Byzantine", "Cuban", "paperclip"]},
        "closure_type":  {"label": "Closure type",   "values": ["lobster claw", "toggle", "box clasp", "fold-over", "magnetic"]},
        "metal_type":    {"label": "Metal type",     "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":  {"label": "Metal finish",   "values": UNIVERSAL_METAL_FINISH},
        "band_width":    {"label": "Band width",     "values": ["delicate (1-2mm)", "thin (3-4mm)", "medium (5-7mm)", "wide (8-12mm)"]},
        "detailing":     {"label": "Detailing",      "values": UNIVERSAL_DETAILING},
    },
    "statue": {
        "style":       {"label": "Style",       "values": UNIVERSAL_STYLES},
        "metal_type":  {"label": "Metal type",  "values": UNIVERSAL_METAL_TYPE},
        "metal_finish":{"label": "Metal finish","values": UNIVERSAL_METAL_FINISH},
        "base_type":   {"label": "Base type",   "values": ["flat square", "round pedestal", "oval plinth", "natural rock", "no base/freestanding"]},
        "detailing":   {"label": "Detailing",   "values": UNIVERSAL_DETAILING},
    },
}

STONE_TYPES = ["ring", "pendant", "earring", "bangle", "necklace", "bracelet"]


# ============================================================================
# FAL.AI FUNCTIONS
# ============================================================================

def fal_upload(fal_key, img_bytes):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    return fal_client.upload(img_bytes, "image/png")


def fal_caption(fal_key, image_url):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    result = fal_client.subscribe(
        "fal-ai/florence-2-large/more-detailed-caption",
        arguments={"image_url": image_url},
    )
    if isinstance(result, dict):
        return result.get("results", str(result))
    return str(result)


def detect_type_from_caption(caption):
    cl = caption.lower()
    for jtype, kws in {
        "earring": ["earring", "ear ring"],
        "bangle":  ["bangle", "cuff bracelet", "cuff"],
        "bracelet":["bracelet", "wristband"],
        "necklace":["necklace", "choker"],
        "pendant": ["pendant", "locket"],
        "ring":    ["ring", "band", "solitaire"],
        "statue":  ["statue", "figurine", "sculpture"],
    }.items():
        for kw in kws:
            if kw in cl:
                return jtype
    return "ring"


def detect_stone_counts(caption):
    cl = caption.lower()
    counts = {"main": 1, "side": 0, "accent": 0}
    if "no stone" in cl or "plain band" in cl or "no gem" in cl:
        counts["main"] = 0
    if "three-stone" in cl or "three stone" in cl:
        counts["main"] = 3
    if "five-stone" in cl:
        counts["main"] = 5
    if any(w in cl for w in ["side stone", "side diamond", "flanking"]):
        counts["side"] = 2
    elif any(w in cl for w in ["channel", "row of", "line of"]):
        counts["side"] = 6
    if any(w in cl for w in ["pave", "pavé", "accent", "small diamond", "melee", "studded", "encrusted"]):
        counts["accent"] = 12
    elif any(w in cl for w in ["halo", "surrounded by"]):
        counts["accent"] = 10
    if counts["side"] == 0 and counts["accent"] == 0:
        if any(w in cl for w in ["diamonds", "stones", "gems"]):
            counts["accent"] = 6
    return counts


def fal_edit(fal_key, source_url, prompt):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    result = fal_client.subscribe(
        "fal-ai/flux-2/turbo/edit",
        arguments={
            "image_urls": [source_url],
            "prompt": prompt,
            "num_images": 1,
            "num_inference_steps": 6,
            "guidance_scale": 15,
        },
    )
    if isinstance(result, dict):
        images = result.get("images", [])
        if images and isinstance(images[0], dict):
            return images[0].get("url")
    return None


# ============================================================================
# STONE PROMPT BUILDER
# ============================================================================

def build_stone_prompt(jewelry_type, stone_cat_key, sub_aspect, new_value, counts):
    cat = STONE_CATEGORIES[stone_cat_key]
    pos = cat["position"]
    count = counts.get(pos, 0)

    # Make sure we only forbid adding stones to the OTHER positions, 
    # otherwise it contradicts our instruction to add stones here.
    pos_map = {
        "main": (
            "center/main",
            "Do NOT touch side or accent stones. Do NOT add new side or accent stones.",
        ),
        "side": (
            "side",
            "Do NOT touch the center/main stone or accent stones. Do NOT add new center or accent stones.",
        ),
        "accent": (
            "accent/pave",
            "Do NOT touch the center/main stone or side stones. Do NOT add new center or side stones.",
        ),
    }
    pos_desc, other_desc = pos_map[pos]
    base = f"{JEWELRY_CONTEXT}Edit this {jewelry_type}: "

    # --- LOGIC FOR ADDING STONES (Count == 0) ---
    if count == 0:
        add_note = f"The original currently has NO {pos} stones. You must ADD new {pos} stones seamlessly into the metal body."
        prompts = {
            "setting": f"{base}add new {pos_desc} stones using a {new_value} setting into the metalwork. {add_note} {other_desc} Keep same angle, lighting, background.",
            "shape": f"{base}add new {new_value} cut {pos_desc} stones into the metalwork. {add_note} {other_desc} Keep same metal, angle, lighting.",
            "style": f"{base}add new {pos_desc} stones in a {new_value} layout. {add_note} {other_desc} Keep same metal, angle, lighting.",
            "prong": f"{base}add new {pos_desc} stones secured with {new_value} prongs. {add_note} {other_desc} Keep same metal, angle.",
            "gemstone": f"{base}add new natural {new_value} {pos_desc} stones. {add_note} {other_desc} Keep same metal, angle, lighting.",
        }
        return prompts.get(sub_aspect)

    # --- LOGIC FOR MODIFYING EXISTING STONES (Count > 0) ---
    count_note = f"The original has exactly {count} {pos} stone(s) — keep exactly {count}, no more, no less."
    prompts = {
        "setting": (
            f"{base}change only how the {pos_desc} stones are mounted to a "
            f"jewelry-style {new_value} setting. The stones must sit naturally "
            f"inside the metalwork. {count_note} {other_desc} "
            f"Keep same stone type, shape, color, metal, angle, lighting, background."
        ),
        "shape": (
            f"{base}replace the {pos_desc} stone(s) with {new_value} cut stones "
            f"fitted naturally into the existing metal settings. "
            f"{count_note} {other_desc} "
            f"Keep same metal, stone color, angle, lighting, background."
        ),
        "style": (
            f"{base}rearrange the {pos_desc} stones into a jewelry-style "
            f"{new_value} layout within the existing metalwork. "
            f"{count_note} {other_desc} "
            f"Keep same stone type, color, metal, angle, lighting, background."
        ),
        "prong": (
            f"{base}change the {pos_desc} stone prongs to jewelry-style "
            f"{new_value}. {count_note} {other_desc} "
            f"Keep same stones, colors, count, metal, angle, lighting, background."
        ),
        "gemstone": (
            f"{base}replace the {pos_desc} stone(s) with natural {new_value} "
            f"gemstone(s) fitted into the existing settings. "
            f"{count_note} {other_desc} "
            f"Keep same metal, settings, angle, lighting, background."
        ),
    }
    return prompts.get(sub_aspect)


# ============================================================================
# NON-STONE PROMPT BUILDER
# ============================================================================

def build_nonstone_prompt(jewelry_type, param, new_value, counts):
    total_stones = sum(counts.values())
    has_stones = total_stones > 0

    cnames = {
        "style": "overall style",
        "shank_style": "shank",
        "head_type": "head/crown",
        "metal_type": "metal",
        "metal_finish": "metal finish/surface",
        "shoulder_style": "shoulders",
        "gallery_style": "gallery",
        "detailing": "detailing/ornamentation",
        "pendant_shape": "pendant shape",
        "frame_style": "frame",
        "bail_type": "bail",
        "earring_type": "earring type",
        "silhouette_shape": "silhouette shape",
        "closure_type": "closure/back",
        "drop_length": "drop length",
        "bangle_type": "bangle form",
        "band_width": "band width",
        "necklace_type": "necklace style",
        "chain_style": "chain link style",
        "link_shape": "link shape",
        "clasp_type": "clasp",
        "bracelet_type": "bracelet style",
        "link_style": "link style",
        "base_type": "base/pedestal",
    }
    comp = cnames.get(param, param.replace("_", " "))
    base = f"{JEWELRY_CONTEXT}Edit this {jewelry_type}: "

    # --- STYLE: metalwork only, stone-aware ---
    if param == "style":
        stone_guard = (
            "If the original has stones, keep the exact same stones, colors, "
            "types, and count. Stone arrangement may adjust but use only the "
            "same stone types already present."
        ) if has_stones else (
            "The original has NO stones — do NOT add any gemstones, diamonds, "
            "or colored stones. Keep it stone-free."
        )
        return (
            f"{base}transform the metalwork and ornamental design language to "
            f"a {new_value} aesthetic. Only modify the metal surfaces, metal "
            f"patterns, metal textures, engravings, filigree, and ornamental "
            f"metalwork. Reimagine the metalwork as if a {new_value} craftsman "
            f"designed it. Do NOT add any new colored gemstones. Do NOT change "
            f"existing stone colors. Do NOT replace diamonds with colored stones "
            f"or vice versa. {stone_guard} Keep same metal color (gold stays "
            f"gold, silver stays silver). Same angle, lighting, and background."
        )

    # --- ALL OTHER PARAMS: 4 random variants ---
    stone_guard = (
        "Do not change any stones, gemstones, stone colors, or stone count."
    ) if has_stones else (
        "Do not add any stones or gemstones. Keep stone-free."
    )

    variants = [
        (
            f"{base}modify the {comp} to a jewelry-style {new_value}. "
            f"This is a goldsmith term — reshape the metal to create a "
            f"{new_value} {comp}. The edit must blend seamlessly into the "
            f"existing piece as if it was always made this way. "
            f"{stone_guard} Keep everything else identical — same angle, "
            f"lighting, background, proportions, metal color."
        ),
        (
            f"{base}redesign the {comp} as a jewelry-style {new_value}. "
            f"Integrate the {new_value} {comp} naturally into the existing "
            f"metalwork — no overlays, no pasting. It must look like a single "
            f"manufactured piece, not a composite. "
            f"{stone_guard} Preserve same angle, lighting, background, "
            f"proportions, metal color, silhouette."
        ),
        (
            f"{base}replace the {comp} with a {new_value} version using "
            f"standard jewelry fabrication. The {new_value} {comp} should be "
            f"part of the metal body, not placed on top. No floating elements, "
            f"no stacking, no literal object placement. "
            f"{stone_guard} Same angle, lighting, background, metal color, "
            f"proportions."
        ),
        (
            f"{base}change the {comp} to {new_value} in the jewelry/goldsmith "
            f"sense. Reshape the existing metal to form a {new_value} {comp} — "
            f"it must be integrated into the band/body. Do not place any object "
            f"or element on top of the jewelry. "
            f"{stone_guard} Everything else stays exactly the same."
        ),
    ]
    return random.choice(variants)


# ============================================================================
# NEW VARIATION GENERATOR (No loops, zero duplicates mathematically guaranteed)
# ============================================================================

def gen_all(jtype, sel_ns, sel_st, num, counts):
    """
    Builds a flat pool of ALL possible unique prompt combinations based on selections,
    shuffles them, and pulls out exactly `num` items. No duplicates allowed.
    """
    pool = []

    # 1. Gather all unique non-stone options
    for pn in sel_ns:
        for val in NON_STONE_PARAMS[jtype][pn]["values"]:
            prompt = build_nonstone_prompt(jtype, pn, val, counts)
            pool.append({
                "prompt": prompt,
                "label": f"{NON_STONE_PARAMS[jtype][pn]['label']} → {val}",
                "new": val,
                "sub": pn
            })

    # 2. Gather all stone options (Allows adding even if counts == 0)
    for skey in sel_st:
        cat = STONE_CATEGORIES[skey]
        for sub, values in cat["data"].items():
            for val in values:
                prompt = build_stone_prompt(jtype, skey, sub, val, counts)
                if prompt:
                    if sub != "gemstone":
                        lbl = f"{cat['label']} {sub.capitalize()} → {val}"
                    else:
                        lbl = f"{cat['label']} → {val}"
                    pool.append({
                        "prompt": prompt,
                        "label": lbl,
                        "new": val,
                        "sub": sub
                    })

    sample_size = min(num, len(pool))
    selected_variations = random.sample(pool, sample_size)

    for i, v in enumerate(selected_variations):
        v["index"] = i + 1

    return selected_variations


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # ---- SIDEBAR ----
    with st.sidebar:
        st.markdown("## 🔑 Fal.ai API Key")
        fal_key = st.text_input(
            label="Fal.ai API Key",
            type="password",
            placeholder="Your FAL_KEY...",
            help="https://fal.ai/dashboard/keys",
        )
        if fal_key:
            st.success("API key set", icon="✅")
        else:
            st.warning("API key required", icon="⚠️")

        st.divider()
        st.markdown("## 💎 Stone Options")
        st.markdown("**Diamond:** Main · Side · Accent")
        st.markdown("**Colored:** Main · Side · Accent")

        st.divider()
        st.markdown("## 🔒 Smart rules")
        st.markdown("• All terms = jewelry terminology")
        st.markdown("• No literal objects placed on ring")
        st.markdown("• Stone count=0 → will command AI to add stones")
        st.markdown("• Style → only changes metalwork")
        st.markdown("• Mathematical guarantee of no duplicate variations")

    # ---- HEADER ----
    st.markdown(
        '<div class="main-header">'
        '<h1>💎 JewelBench — Bulk Variation Generator</h1>'
        '<p>Upload → detect → select → generate precise edits — all via Fal.ai</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- SESSION STATE ----
    for k, d in [
        ("analysis", None),
        ("source_bytes", None),
        ("fal_url", None),
        ("generated", []),
        ("stone_counts", {"main": 1, "side": 0, "accent": 0}),
    ]:
        if k not in st.session_state:
            st.session_state[k] = d

    # ================================================================
    # STEP 1: Upload
    # ================================================================
    st.markdown(
        '<p class="section-title">Step 1 — Upload source image</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="section-sub">Upload a jewelry photo. Florence-2 detects type + stone counts.</p>',
        unsafe_allow_html=True,
    )

    col_up, col_prev = st.columns([1, 1])
    with col_up:
        uploaded = st.file_uploader(
            label="Upload jewelry image",
            type=["png", "jpg", "jpeg", "webp"],
            label_visibility="collapsed",
        )
    with col_prev:
        if uploaded:
            st.image(uploaded, caption="Source image", width=280)
        elif st.session_state.source_bytes:
            st.image(st.session_state.source_bytes, caption="Source image", width=280)

    if not fal_key:
        st.info("👈 Enter your Fal.ai API key in the sidebar.")

    if st.button("🔍 Analyze Image", type="primary", disabled=not (uploaded and fal_key)):
        img_bytes = uploaded.getvalue()
        st.session_state.source_bytes = img_bytes
        st.session_state.generated = []
        st.session_state.analysis = None

        with st.spinner("☁️ Uploading..."):
            try:
                st.session_state.fal_url = fal_upload(fal_key, img_bytes)
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        with st.spinner("🔍 Detecting..."):
            try:
                caption = str(fal_caption(fal_key, st.session_state.fal_url))
                st.session_state.analysis = {
                    "type": detect_type_from_caption(caption),
                    "caption": caption,
                }
                st.session_state.stone_counts = detect_stone_counts(caption)
            except Exception as e:
                st.error(f"Detection failed: {e}")
                st.stop()

        st.rerun()

    # ================================================================
    # STEP 2: Detection + Selection
    # ================================================================
    if st.session_state.analysis:
        a = st.session_state.analysis
        auto_type = a["type"]
        caption = a.get("caption", "")
        counts = st.session_state.stone_counts

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="detect-box">'
            f'<div class="detect-type">{TYPE_ICONS.get(auto_type, "💎")} Auto-detected: {auto_type}</div>'
            f'<div class="detect-caption">"{caption[:250]}{"..." if len(caption) > 250 else ""}"</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="stone-counts">'
            f'🔢 <b>Stone counts:</b> Main: {counts["main"]} · Side: {counts["side"]} · '
            f'Accent: {counts["accent"]} — preserved in edits. Selecting a stone with count 0 will prompt the AI to ADD stones.'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Confirm or change type:**")
        jtype = st.selectbox(
            label="Jewelry type",
            options=VALID_TYPES,
            index=VALID_TYPES.index(auto_type),
            format_func=lambda x: f"{TYPE_ICONS.get(x, '💎')} {x.capitalize()}",
        )

        ns = NON_STONE_PARAMS.get(jtype, {})

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">Step 2 — Select what to change</p>',
            unsafe_allow_html=True,
        )

        # Non-stone params
        st.markdown("**⚙️ Structure / Metal / Style / Detail:**")
        pnames = list(ns.keys())
        half = (len(pnames) + 1) // 2
        c1, c2 = st.columns(2)
        sel_ns = []
        for i, pn in enumerate(pnames):
            m = ns[pn]
            col = c1 if i < half else c2
            with col:
                if st.checkbox(
                    label=f"{m['label']}  ({len(m['values'])} options)",
                    key=f"cb_{jtype}_{pn}",
                ):
                    sel_ns.append(pn)

        # Stone params
        sel_st = []
        if jtype in STONE_TYPES:
            st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)

            st.markdown("**💎 Diamond stones:**")
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                if st.checkbox(label="💎 Diamond Main (32 sub)", key="cb_dm"):
                    sel_st.append("diamond_main")
            with dc2:
                if st.checkbox(label="💎 Diamond Side (22 sub)", key="cb_ds"):
                    sel_st.append("diamond_side")
            with dc3:
                if st.checkbox(label="💎 Diamond Accent (20 sub)", key="cb_da"):
                    sel_st.append("diamond_accent")

            st.markdown("**🔴 Colored stones:**")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                if st.checkbox(label="🔴 Colored Main (39 sub)", key="cb_cm"):
                    sel_st.append("colored_main")
            with cc2:
                if st.checkbox(label="🔵 Colored Side (27 sub)", key="cb_cs"):
                    sel_st.append("colored_side")
            with cc3:
                if st.checkbox(label="🟢 Colored Accent (24 sub)", key="cb_ca"):
                    sel_st.append("colored_accent")

        # ============================================================
        # STEP 3: Generate
        # ============================================================
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">Step 3 — Generate</p>',
            unsafe_allow_html=True,
        )

        # Calculate exact number of unique value options selected
        total_options = 0
        for pn in sel_ns:
            total_options += len(ns[pn]["values"])

        for skey in sel_st:
            cat = STONE_CATEGORIES.get(skey)
            if cat: # <-- Allows adding the options even if count is 0
                for vals in cat["data"].values():
                    total_options += len(vals)

        gc1, gc2 = st.columns([1, 2])
        with gc1:
            num = st.number_input(
                label="Number of images",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
            )
        with gc2:
            if total_options < num:
                st.error(
                    f"⚠️ Select more parameters. Your current selection gives **{total_options} unique valid options**, "
                    f"but you are requesting **{num} images**."
                )
            else:
                st.success(f"✅ **{total_options} unique options available** — ready to generate {num} images with 0 duplicates.")

        can = total_options >= num and bool(fal_key) and st.session_state.fal_url

        if st.button(
            "🚀 Generate Variations",
            type="primary",
            disabled=not can,
            use_container_width=True,
        ):
            variations = gen_all(jtype, sel_ns, sel_st, num, counts)

            # Distribution stats
            dist = {}
            for v in variations:
                cat = v["label"].split(" → ")[0] if " → " in v["label"] else v["label"]
                dist[cat] = dist.get(cat, 0) + 1
            scols = st.columns(min(len(dist), 5))
            for i, (lb, ct) in enumerate(sorted(dist.items(), key=lambda x: -x[1])):
                if i < 5:
                    with scols[i]:
                        st.metric(label=lb[:25], value=ct)

            # Plan
            with st.expander("📋 Plan & prompts"):
                for v in variations:
                    st.markdown(f"**{v['index']}.** {v['label']}")
                    st.code(v["prompt"], language=None)

            # Generate images
            prog = st.progress(0, text="Starting...")
            gen = []
            for i, v in enumerate(variations):
                prog.progress(
                    (i + 1) / len(variations),
                    text=f"{i + 1}/{len(variations)}: {v['label'][:50]}",
                )
                try:
                    url = fal_edit(fal_key, st.session_state.fal_url, v["prompt"])
                    if url:
                        ir = requests.get(url, timeout=60)
                        gen.append({
                            "bytes": ir.content,
                            "label": v["label"],
                            "new": v["new"],
                            "url": url,
                            "prompt": v["prompt"],
                        })
                except Exception as e:
                    st.warning(f"#{i + 1} failed: {e}")
                if i < len(variations) - 1:
                    time.sleep(0.5)

            prog.empty()
            st.session_state.generated = gen
            st.success(f"✅ Generated {len(gen)}/{len(variations)} images")

    # ================================================================
    # STEP 4: Results
    # ================================================================
    if st.session_state.generated:
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">Results</p>',
            unsafe_allow_html=True,
        )

        imgs = st.session_state.generated
        for rs in range(0, len(imgs), 4):
            cols = st.columns(4)
            for j in range(4):
                ix = rs + j
                if ix < len(imgs):
                    im = imgs[ix]
                    with cols[j]:
                        st.image(im["bytes"], use_container_width=True)
                        st.markdown(f"**{im['label']}**")

        log = [
            {
                "label": i["label"],
                "new": i["new"],
                "url": i["url"],
                "prompt": i["prompt"],
            }
            for i in imgs
        ]
        st.download_button(
            label="📥 Download log (JSON)",
            data=json.dumps(log, indent=2),
            file_name="variations_log.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
