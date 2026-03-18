"""
JewelBench — Bulk Jewelry Variation Generator (Streamlit)
==========================================================
Uses ONLY Fal.ai (single API key):
  - Florence-2 Large → captioning + type detection + stone count detection
  - Flux 2 Turbo Edit → single-component image editing

STONE HIERARCHY:
  Diamond:
    1. Diamond Main Stone    (setting / shape / style / prong)
    2. Diamond Side Stone    (setting / shape / style / prong)
    3. Diamond Accent Stone  (setting / shape / style / prong)
  Colored Stone:
    4. Colored Main Stone    (setting / shape / style / prong / gemstone)
    5. Colored Side Stone    (setting / shape / style / prong / gemstone)
    6. Colored Accent Stone  (setting / shape / style / prong / gemstone)

Florence-2 detects stone counts → prompts preserve exact counts.

RUN:  pip install streamlit fal-client Pillow requests
"""

import streamlit as st
import os, json, random, base64, time, re, requests
from typing import Optional

st.set_page_config(page_title="JewelBench — Bulk Variations", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

# ============================================================================
# CSS
# ============================================================================
st.markdown("""
<style>
    .stApp, .main, [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #1a1a1a !important; }
    section[data-testid="stSidebar"] { background-color: #F8FAFC !important; color: #1a1a1a !important; }
    section[data-testid="stSidebar"] * { color: #1a1a1a !important; }
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stText, label,
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span { color: #1a1a1a !important; }
    .stCheckbox label p, .stCheckbox label span, [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] label span, [data-testid="stCheckbox"] label div {
        color: #1a1a1a !important; font-size: 14px !important; font-weight: 500 !important;
    }
    .stSelectbox div[data-baseweb="select"] span { color: #1a1a1a !important; }
    .stSelectbox div[data-baseweb="select"] { background-color: #FFFFFF !important; }
    .stSlider label, .stSlider p, .stSlider span { color: #1a1a1a !important; }
    .main-header { background: linear-gradient(135deg, #1B3A5C 0%, #2E75B6 100%); padding: 24px 32px; border-radius: 12px; margin-bottom: 24px; }
    .main-header h1 { color: #FFFFFF !important; font-size: 28px !important; font-weight: 600 !important; margin: 0 !important; }
    .main-header p { color: rgba(255,255,255,0.85) !important; font-size: 14px !important; margin: 4px 0 0 0 !important; }
    .section-title { font-size: 18px; font-weight: 600; color: #1B3A5C !important; margin: 0 0 4px 0; }
    .section-sub { font-size: 13px; color: #4a5568 !important; margin: 0 0 16px 0; }
    .detect-box { background: #F0F7FF; border: 2px solid #2E75B6; border-radius: 12px; padding: 20px 24px; margin: 16px 0; }
    .detect-type { font-size: 22px; font-weight: 700; color: #1B3A5C !important; text-transform: capitalize; }
    .detect-caption { font-size: 13px; color: #4a5568 !important; margin-top: 8px; line-height: 1.5; font-style: italic; }
    .stone-counts { background: #FFF7ED; border: 1px solid #FDBA74; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 13px; color: #9A3412 !important; }
    .blue-divider { height: 3px; background: linear-gradient(90deg, #2E75B6, transparent); border: none; border-radius: 2px; margin: 24px 0; }
    .stProgress > div > div > div > div { background-color: #2E75B6; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# STONE SYSTEM — 6 categories, each with sub-options
# ============================================================================

DIAMOND_MAIN = {
    "setting": ["4-prong claw","6-prong claw","full bezel","half bezel","tension set","cathedral bezel","collet set","gypsy/flush set"],
    "shape":   ["round brilliant","princess cut","oval","emerald cut","cushion","pear","marquise","radiant","asscher","heart"],
    "style":   ["solitaire","halo","double halo","three-stone center","cluster","bezel solitaire","tension solitaire"],
    "prong":   ["round prong","pointed/claw prong","V-prong","double prong","tab prong","button prong","tulip prong"],
}
DIAMOND_SIDE = {
    "setting": ["channel set","pave set","bezel set","bar set","invisible set","U-cut pave"],
    "shape":   ["round brilliant","baguette","tapered baguette","princess cut","trillion"],
    "style":   ["pave band","channel row","eternity set","half-eternity","three-stone side pair","graduated row"],
    "prong":   ["shared prong","fish-tail set","bright-cut pave","U-cut","scalloped set"],
}
DIAMOND_ACCENT = {
    "setting": ["micro pave","channel set","flush/gypsy set","bar set","bead set","burnish set"],
    "shape":   ["round brilliant","single-cut round","baguette","marquise","french cut"],
    "style":   ["scattered accent","pave trail","milgrain-set cluster","flush scattered","halo ring"],
    "prong":   ["bead set (no prong)","micro-prong","shared prong","bright-cut"],
}

COLORED_GEMSTONES = ["ruby","blue sapphire","emerald","tanzanite","morganite","aquamarine","amethyst","topaz","garnet","citrine","peridot","opal","black onyx","alexandrite","tourmaline","spinel"]
COLORED_SIDE_GEMS = ["ruby","blue sapphire","emerald","pink sapphire","tsavorite","amethyst","yellow sapphire","orange sapphire"]
COLORED_ACCENT_GEMS = ["ruby","blue sapphire","emerald","pink sapphire","black diamond","tsavorite","amethyst","diamond (colorless)"]

COLORED_MAIN = {
    "setting": ["4-prong claw","6-prong claw","full bezel","half bezel","tension set","cathedral bezel","collet set","gypsy/flush set"],
    "shape":   ["oval","emerald cut","cushion","pear","round brilliant","cabochon","marquise","trillion","sugarloaf cabochon"],
    "style":   ["solitaire","halo","double halo","three-stone center","cluster","bezel solitaire"],
    "prong":   ["round prong","pointed/claw prong","V-prong","double prong","tab prong","button prong"],
    "gemstone": COLORED_GEMSTONES,
}
COLORED_SIDE = {
    "setting": ["channel set","pave set","bezel set","bar set","invisible set","U-cut pave"],
    "shape":   ["round","baguette","tapered baguette","princess cut","trillion","oval"],
    "style":   ["pave band","channel row","eternity set","half-eternity","three-stone side pair","graduated row","alternating color"],
    "prong":   ["shared prong","fish-tail set","bright-cut pave","U-cut","scalloped set"],
    "gemstone": COLORED_SIDE_GEMS,
}
COLORED_ACCENT = {
    "setting": ["micro pave","channel set","flush/gypsy set","bar set","bead set","burnish set"],
    "shape":   ["round","baguette","marquise","french cut","princess cut"],
    "style":   ["scattered accent","pave trail","milgrain-set cluster","flush scattered","halo ring"],
    "prong":   ["bead set (no prong)","micro-prong","shared prong","bright-cut"],
    "gemstone": COLORED_ACCENT_GEMS,
}

STONE_CATEGORIES = {
    "diamond_main":   {"label": "💎 Diamond — Main Stone",    "icon": "💎", "data": DIAMOND_MAIN,   "type": "diamond",  "position": "main"},
    "diamond_side":   {"label": "💎 Diamond — Side Stones",   "icon": "💎", "data": DIAMOND_SIDE,   "type": "diamond",  "position": "side"},
    "diamond_accent": {"label": "💎 Diamond — Accent Stones", "icon": "💎", "data": DIAMOND_ACCENT, "type": "diamond",  "position": "accent"},
    "colored_main":   {"label": "🔴 Colored — Main Stone",    "icon": "🔴", "data": COLORED_MAIN,   "type": "colored",  "position": "main"},
    "colored_side":   {"label": "🔵 Colored — Side Stones",   "icon": "🔵", "data": COLORED_SIDE,   "type": "colored",  "position": "side"},
    "colored_accent": {"label": "🟢 Colored — Accent Stones", "icon": "🟢", "data": COLORED_ACCENT, "type": "colored",  "position": "accent"},
}

# ============================================================================
# NON-STONE PARAMS (no stone-related entries here)
# ============================================================================

MIN_PARAMS_RULES = {5: 1, 10: 1, 20: 2, 30: 2, 40: 3, 50: 4}
def get_min_params(n):
    for t in sorted(MIN_PARAMS_RULES.keys(), reverse=True):
        if n >= t: return MIN_PARAMS_RULES[t]
    return 1

TYPE_ICONS = {"ring": "💍", "pendant": "📿", "earring": "✨", "bangle": "⭕", "necklace": "📿", "bracelet": "⛓️", "statue": "🗿"}
VALID_TYPES = ["ring", "pendant", "earring", "bangle", "necklace", "bracelet", "statue"]

NON_STONE_PARAMS = {
    "ring": {
        "shank_style":    {"label": "Shank style",   "values": ["knife-edge","tapered","comfort-fit rounded","flat band","euro-shank","split-shank","twisted rope","bypass-swirl","open lattice","cathedral shank","double-rail","scalloped gallery shank","architectural ribbed","bamboo textured","braided wire"]},
        "head_type":      {"label": "Head type",      "values": ["basket mount","cathedral","bezel frame","low-profile flush","crown head","suspended crown","tension bridge","geometric frame","double halo head","raised pedestal","lotus head","trellis/lattice head","compass prong head","split-claw head"]},
        "metal_type":     {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","14K yellow gold","sterling silver"]},
        "metal_finish":   {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "shoulder_style": {"label": "Shoulder style", "values": ["plain","pave-set","tapered baguette","milgrain edged"]},
        "gallery_style":  {"label": "Gallery",        "values": ["open gallery","closed gallery","filigree gallery","hidden halo gallery","pierced gallery","scroll gallery","lattice gallery","crown gallery"]},
        "edge_finish":    {"label": "Edge finish",    "values": ["plain","milgrain","rope edge","knife edge"]},
    },
    "pendant": {
        "pendant_shape":   {"label": "Pendant shape",  "values": ["round","oval","teardrop","heart","bar","disc","geometric hexagon","marquise silhouette","cross","star","crescent moon","kite/rhombus","shield","pear drop","octagon"]},
        "frame_style":     {"label": "Frame style",    "values": ["open frame","closed back","halo frame","minimal wire frame","double frame","vintage scroll frame","art deco geometric frame","floating/tension frame","cage/lantern frame","bezel wrap frame"]},
        "bail_type":       {"label": "Bail type",      "values": ["fixed bail","hidden bail","tube bail","diamond-set bail","split bail","rabbit ear bail","enhancer clip bail","hinged bail","omega bail","double loop bail"]},
        "metal_type":      {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":    {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "border_detail":   {"label": "Border detail",  "values": ["none","milgrain border","rope border","scalloped edge"]},
        "motif":           {"label": "Motif",          "values": ["none","floral","celestial star/moon","infinity symbol"]},
        "layer_dimension": {"label": "Dimension",      "values": ["flat single layer","domed","concave dish","multi-layer stacked"]},
    },
    "earring": {
        "earring_type":     {"label": "Earring type",   "values": ["stud","drop","hoop","huggie","chandelier","climber","threader","ear cuff","jacket","dangle","crawler","front-back (peek-a-boo)","shield/disc"]},
        "silhouette_shape": {"label": "Silhouette",     "values": ["round","oval","teardrop","geometric angular","linear bar","fan/semicircle","floral cluster","abstract organic","kite/diamond","starburst","crescent","triangular","cascading tier"]},
        "closure_type":     {"label": "Closure type",   "values": ["push back","screw back","lever back","hook/shepherd","hinged","latch back","snap post","omega clip","threader chain","ear wire with bead stop"]},
        "frame_style":      {"label": "Frame style",    "values": ["open","closed","filigree","wire wrap","sculpted solid","cage/lantern","lattice","halo surround","art deco geometric","floating/tension"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "drop_length":      {"label": "Drop length",    "values": ["flush to ear (stud)","short drop (1-2cm)","medium drop (3-4cm)","long drop (5-7cm)"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","celestial","geometric"]},
    },
    "bangle": {
        "bangle_type":      {"label": "Bangle type",    "values": ["solid closed","hinged","open cuff","coil wrap","stacking thin","bypass cuff","expandable","mesh flex","articulated segment","snake/serpenti","torque","spring-loaded"]},
        "closure_type":     {"label": "Closure type",   "values": ["slip-on (no clasp)","hinged with clasp","box clasp","magnetic clasp","toggle clasp","hook and eye","push-pull clasp","barrel screw","fold-over safety"]},
        "cross_section":    {"label": "Cross section",  "values": ["round tube","flat band","D-profile","oval tube","knife edge","square tube","triangular","concave channel","twisted wire","half-round","hexagonal"]},
        "band_width":       {"label": "Band width",     "values": ["slim (3mm)","medium (6mm)","wide (10mm)","extra wide (15mm)"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "surface_pattern":  {"label": "Surface pattern","values": ["none/plain","hammered texture","diamond-cut facets","twisted cable","woven/braided","bark texture","geometric etched","brushed linear","granulation","filigree overlay","herringbone"]},
        "edge_treatment":   {"label": "Edge treatment", "values": ["plain smooth","milgrain","rope border","scalloped"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","celestial","geometric"]},
    },
    "necklace": {
        "necklace_type":   {"label": "Necklace type",  "values": ["chain","pendant chain","choker","station necklace","lariat/Y-chain","collar","multi-strand","statement bib","rivière","omega","festoon","rope length","layered set"]},
        "chain_style":     {"label": "Chain style",    "values": ["cable link","box chain","curb link","rope chain","figaro","snake chain","Singapore twist","wheat chain","paperclip link","ball/bead chain","Byzantine","Venetian box","herringbone flat","mariner/anchor"]},
        "pendant_element": {"label": "Pendant element","values": ["none (chain only)","solitaire drop","bar pendant","disc/coin","initial letter","locket","cross","gemstone cluster","geometric charm","medallion","tassel drop","heart silhouette"]},
        "link_shape":      {"label": "Link shape",     "values": ["round","oval","elongated rectangle","flat disc","N/A (solid chain)","textured nugget","twisted figure-8","marquise link","heart link","hammered organic","graduated sizing"]},
        "metal_type":      {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":    {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","diamond-cut faceted"]},
        "clasp_type":      {"label": "Clasp type",     "values": ["lobster claw","spring ring","toggle","box clasp","magnetic"]},
        "surface_texture": {"label": "Surface texture","values": ["smooth","hammered links","twisted links","diamond-cut facets"]},
        "chain_thickness": {"label": "Thickness",      "values": ["delicate (0.5-1mm)","thin (1-1.5mm)","medium (2-3mm)","thick (4-5mm)"]},
        "motif":           {"label": "Motif",          "values": ["none","floral","celestial","geometric","infinity"]},
    },
    "bracelet": {
        "bracelet_type":   {"label": "Bracelet type",  "values": ["chain link","tennis","cuff","charm","bar/ID","mesh","bangle style","wrap","beaded","hinged segment","serpenti/snake","sliding/bolo","station"]},
        "link_style":      {"label": "Link style",     "values": ["cable","curb","figaro","rope","box","N/A (solid)","Byzantine","Cuban","paperclip","mariner/anchor","wheat","herringbone","Venetian"]},
        "closure_type":    {"label": "Closure type",   "values": ["lobster claw","toggle","box clasp","fold-over","magnetic"]},
        "metal_type":      {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":    {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "surface_texture": {"label": "Surface texture","values": ["smooth","hammered","twisted cable","braided","diamond-cut","bark texture","granulated","brushed linear","woven mesh","filigree overlay","satin matte","sandblasted"]},
        "band_width":      {"label": "Band width",     "values": ["delicate (1-2mm)","thin (3-4mm)","medium (5-7mm)","wide (8-12mm)"]},
        "edge_treatment":  {"label": "Edge treatment", "values": ["plain","milgrain","rope border","scalloped"]},
        "motif":           {"label": "Motif",          "values": ["none","floral","geometric","celestial"]},
    },
    "statue": {
        "pose":             {"label": "Pose",           "values": ["standing upright","seated","dynamic action","meditative","contrapposto","arms raised","kneeling","reclining","dancing","warrior stance","prayer/namaste","flying/leaping","crouching"]},
        "proportion":       {"label": "Proportion",     "values": ["realistic anatomical","stylized elongated","exaggerated heroic","abstract distorted","chibi/compact","art deco geometric","Botero rounded","Giacometti thin","classical Greek ideal","cubist fragmented"]},
        "surface_detail":   {"label": "Surface detail", "values": ["smooth minimal","highly detailed/realistic","abstract textured","faceted geometric","organic flowing","hammered rustic","filigree overlay","bas-relief carved","weathered/eroded","crystalline fractured"]},
        "theme":            {"label": "Theme",          "values": ["classical","contemporary modern","art deco","minimalist","nature-inspired","gothic","baroque","brutalist","cyberpunk/futuristic","tribal/ethnic","renaissance","steampunk"]},
        "metal_type":       {"label": "Metal type",     "values": ["sterling silver","bronze","18K yellow gold","platinum","brass"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","patina aged","antiqued oxidized","satin"]},
        "base_type":        {"label": "Base type",      "values": ["flat square","round pedestal","oval plinth","natural rock","no base/freestanding"]},
        "base_material":    {"label": "Base material",  "values": ["matching metal","marble/stone","wood","onyx"]},
        "clothing_drape":   {"label": "Clothing/drape", "values": ["nude/minimal","flowing robes","fitted garment","armor/warrior","N/A (animal/abstract)"]},
        "texture_contrast": {"label": "Texture contrast","values": ["uniform texture","mixed (polished + matte)","rough + smooth contrast"]},
    },
}

# Types that have stone options (statue doesn't)
STONE_TYPES = ["ring", "pendant", "earring", "bangle", "necklace", "bracelet"]


# ============================================================================
# FAL.AI functions
# ============================================================================

def fal_upload(fal_key, img_bytes):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    return fal_client.upload(img_bytes, "image/png")

def fal_caption(fal_key, image_url):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    result = fal_client.subscribe("fal-ai/florence-2-large/more-detailed-caption", arguments={"image_url": image_url})
    if isinstance(result, dict):
        return result.get("results", str(result))
    return str(result)

def detect_type_from_caption(caption):
    cl = caption.lower()
    for jtype, keywords in {
        "earring": ["earring","ear ring","stud earring","hoop earring"],
        "bangle": ["bangle","cuff bracelet","cuff"],
        "bracelet": ["bracelet","wristband","tennis bracelet"],
        "necklace": ["necklace","chain necklace","choker"],
        "pendant": ["pendant","locket"],
        "ring": ["ring","band","solitaire","engagement"],
        "statue": ["statue","figurine","sculpture","figure","bust"],
    }.items():
        for kw in keywords:
            if kw in cl: return jtype
    return "ring"

def detect_stone_counts(caption):
    """Parse Florence-2 caption to estimate stone counts. Returns dict."""
    cl = caption.lower()
    counts = {"main": 1, "side": 0, "accent": 0}

    # Main stone — usually 1
    if any(w in cl for w in ["solitaire","center stone","large stone","main stone","single diamond","single gem"]):
        counts["main"] = 1
    elif "three-stone" in cl or "three stone" in cl:
        counts["main"] = 3
    elif "five-stone" in cl or "five stone" in cl:
        counts["main"] = 5

    # Side stones
    if any(w in cl for w in ["side stone","side diamond","flanking"]):
        counts["side"] = 2
    elif "baguette" in cl and "side" in cl:
        counts["side"] = 2
    elif any(w in cl for w in ["channel","row of","line of"]):
        counts["side"] = 6

    # Accent/pave
    if any(w in cl for w in ["pave","pavé","accent","small diamond","melee","studded","encrusted"]):
        counts["accent"] = 12
    elif any(w in cl for w in ["halo","surrounded by"]):
        counts["accent"] = 10

    # Fallback: if caption mentions "diamond" or "stone" generically
    if counts["side"] == 0 and counts["accent"] == 0:
        if any(w in cl for w in ["diamonds","stones","gems","gemstones","jewels"]):
            counts["accent"] = 6

    return counts

def fal_edit(fal_key, source_url, prompt):
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    result = fal_client.subscribe("fal-ai/flux-2/turbo/edit", arguments={
        "image_urls": [source_url], "prompt": prompt,
        "num_images": 1, "num_inference_steps": 6, "guidance_scale": 15,
    })
    if isinstance(result, dict):
        images = result.get("images", [])
        if images and isinstance(images[0], dict):
            return images[0].get("url")
    return None


# ============================================================================
# STONE PROMPT BUILDER — uses stone counts from Florence-2
# ============================================================================

def build_stone_prompt(jewelry_type, stone_cat_key, sub_aspect, new_value, counts):
    """Build precise stone edit prompt that preserves stone counts."""
    cat = STONE_CATEGORIES[stone_cat_key]
    position = cat["position"]  # main / side / accent
    stone_type = cat["type"]    # diamond / colored

    count = counts.get(position, 1)
    count_str = f"exactly {count}" if count > 0 else ""

    if position == "main":
        position_desc = "center/main"
        other_desc = "Do NOT touch the side stones or accent stones. Keep them exactly as they are."
        count_note = f"There should be {count_str} main stone(s)." if count_str else ""
    elif position == "side":
        position_desc = "side"
        other_desc = "Do NOT touch the center/main stone or accent stones. Keep them exactly as they are."
        count_note = f"There should be {count_str} side stone(s) in the same positions." if count_str else ""
    else:
        position_desc = "accent/pave"
        other_desc = "Do NOT touch the center/main stone or side stones. Keep them exactly as they are."
        count_note = f"Keep the same number of accent stones." if count > 0 else ""

    gem_name = "diamond" if stone_type == "diamond" else new_value if sub_aspect == "gemstone" else ""

    if sub_aspect == "setting":
        return (
            f"Edit this {jewelry_type}: completely remove the existing {position_desc} stone setting "
            f"and replace it with a {new_value} setting. "
            f"The stones must sit naturally inside the new setting, not stacked on top. "
            f"{count_note} {other_desc} "
            f"Keep the same stone type, shape, and color. Keep the same metal, angle, lighting, background."
        )
    elif sub_aspect == "shape":
        return (
            f"Edit this {jewelry_type}: completely remove the existing {position_desc} stone(s) "
            f"and replace with {new_value} cut {'diamonds' if stone_type == 'diamond' else 'gemstones'}. "
            f"The new stones must sit naturally inside the existing settings, not on top. "
            f"{count_note} {other_desc} "
            f"Keep the same metal, angle, lighting, background, and overall proportions."
        )
    elif sub_aspect == "style":
        return (
            f"Edit this {jewelry_type}: change the {position_desc} stone arrangement/style "
            f"to a {new_value} layout. "
            f"Remove the existing arrangement and replace with {new_value}. "
            f"{count_note} {other_desc} "
            f"Keep the same metal, angle, lighting, background, and overall proportions."
        )
    elif sub_aspect == "prong":
        return (
            f"Edit this {jewelry_type}: change the {position_desc} stone prong/setting finish "
            f"to {new_value}. Replace how the {position_desc} stones are held with {new_value}. "
            f"{count_note} {other_desc} "
            f"Keep the same stones, stone colors, metal, angle, lighting, background."
        )
    elif sub_aspect == "gemstone":
        return (
            f"Edit this {jewelry_type}: completely remove the existing {position_desc} stone(s) "
            f"and replace with natural {new_value} gemstone(s) in the exact same positions and sizes. "
            f"The {new_value} must sit naturally inside the existing settings, not stacked on top. "
            f"{count_note} {other_desc} "
            f"Keep the same metal, settings, angle, lighting, background, and overall proportions."
        )

    return f"Edit this {jewelry_type}: change the {position_desc} stones."


# ============================================================================
# NON-STONE PROMPT BUILDER
# ============================================================================

def build_nonstone_prompt(jewelry_type, param, new_value):
    component_names = {
        "shank_style": "shank", "head_type": "head/crown", "metal_type": "metal",
        "metal_finish": "metal finish/surface", "shoulder_style": "shoulders",
        "gallery_style": "gallery", "edge_finish": "edge finish",
        "pendant_shape": "pendant shape", "frame_style": "frame", "bail_type": "bail",
        "border_detail": "border", "motif": "decorative motif",
        "layer_dimension": "depth/dimension", "earring_type": "earring type",
        "silhouette_shape": "silhouette shape", "closure_type": "closure/back",
        "drop_length": "drop length", "bangle_type": "bangle form",
        "cross_section": "cross-section profile", "band_width": "band width",
        "surface_pattern": "surface pattern", "edge_treatment": "edge treatment",
        "necklace_type": "necklace style", "chain_style": "chain link style",
        "pendant_element": "pendant element", "link_shape": "link shape",
        "clasp_type": "clasp", "surface_texture": "surface texture",
        "chain_thickness": "chain thickness", "bracelet_type": "bracelet style",
        "link_style": "link style", "pose": "pose",
        "proportion": "body proportions", "surface_detail": "surface detail level",
        "theme": "artistic theme", "base_type": "base/pedestal",
        "base_material": "base material", "clothing_drape": "clothing/draping",
        "texture_contrast": "texture contrast",
    }
    component = component_names.get(param, param.replace("_", " "))
    return (
        f"Edit this {jewelry_type}: replace the existing {component} with a {new_value}. "
        f"Remove the original {component} completely and replace with {new_value}. "
        f"Do not stack or layer. Do not change any stones, gemstones, or stone colors. "
        f"The result should look like the {jewelry_type} was always made with a {new_value} {component}. "
        f"Keep everything else identical — same angle, lighting, background, proportions, stones, overall design."
    )


# ============================================================================
# VARIATION GENERATORS
# ============================================================================

def generate_stone_variation(jewelry_type, stone_cat_key, counts):
    """Generate one stone variation — picks a random sub-aspect and value."""
    cat = STONE_CATEGORIES[stone_cat_key]
    data = cat["data"]
    sub_aspects = list(data.keys())
    sub = random.choice(sub_aspects)
    val = random.choice(data[sub])
    prompt = build_stone_prompt(jewelry_type, stone_cat_key, sub, val, counts)
    sub_label = sub.capitalize()
    if sub == "gemstone":
        label = f"{cat['label']} → {val}"
    else:
        label = f"{cat['label']} {sub_label} → {val}"
    return {"prompt": prompt, "label": label, "new": val, "sub": sub}

def generate_nonstone_variation(jewelry_type, param, params_dict):
    val = random.choice(params_dict[param]["values"])
    prompt = build_nonstone_prompt(jewelry_type, param, val)
    return {"prompt": prompt, "label": f"{params_dict[param]['label']} → {val}", "new": val, "sub": param}

def generate_all_variations(jewelry_type, selected_nonstone, selected_stones, num, counts):
    all_sources = []
    for p in selected_nonstone:
        all_sources.append(("nonstone", p))
    for s in selected_stones:
        all_sources.append(("stone", s))

    variations, used, idx, att = [], set(), 0, 0
    while len(variations) < num and att < num * 10:
        att += 1
        source_type, source_key = all_sources[idx % len(all_sources)]
        idx += 1

        if source_type == "nonstone":
            v = generate_nonstone_variation(jewelry_type, source_key, NON_STONE_PARAMS[jewelry_type])
        else:
            v = generate_stone_variation(jewelry_type, source_key, counts)

        key = (source_key, v["sub"], v["new"])
        if key in used and att < num * 3:
            continue
        used.add(key)
        v["index"] = len(variations) + 1
        variations.append(v)

    return variations


# ============================================================================
# MAIN
# ============================================================================

def main():
    with st.sidebar:
        st.markdown("## 🔑 Fal.ai API Key")
        fal_key = st.text_input(label="Fal.ai API Key", type="password", placeholder="Your FAL_KEY...", help="https://fal.ai/dashboard/keys")
        if fal_key: st.success("API key set", icon="✅")
        else: st.warning("API key required", icon="⚠️")
        st.divider()
        st.markdown("## 💎 Stone Hierarchy")
        st.markdown("**Diamond stones:**")
        st.markdown("💎 Main · Side · Accent")
        st.markdown("**Colored stones:**")
        st.markdown("🔴 Main · 🔵 Side · 🟢 Accent")
        st.markdown("Each varies: setting, shape, style, prong")
        st.markdown("Colored also varies: gemstone type")
        st.divider()
        st.markdown("Florence-2 detects stone counts → prompts preserve the exact count.")

    st.markdown('<div class="main-header"><h1>💎 JewelBench — Bulk Variation Generator</h1><p>Upload → detect → select → generate precise edits — all via Fal.ai</p></div>', unsafe_allow_html=True)

    for k, d in [("analysis", None), ("source_bytes", None), ("fal_url", None), ("generated", []), ("stone_counts", {"main": 1, "side": 0, "accent": 0})]:
        if k not in st.session_state: st.session_state[k] = d

    # STEP 1
    st.markdown('<p class="section-title">Step 1 — Upload source image</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Upload a jewelry photo. Florence-2 detects type + stone counts.</p>', unsafe_allow_html=True)

    col_up, col_prev = st.columns([1, 1])
    with col_up:
        uploaded = st.file_uploader(label="Upload jewelry image", type=["png","jpg","jpeg","webp"], label_visibility="collapsed")
    with col_prev:
        if uploaded is not None: st.image(uploaded, caption="Source image", width=280)
        elif st.session_state.source_bytes is not None: st.image(st.session_state.source_bytes, caption="Source image", width=280)

    if not fal_key: st.info("👈 Enter your Fal.ai API key in the sidebar.")

    if st.button("🔍 Analyze Image", type="primary", disabled=not (uploaded and fal_key)):
        img_bytes = uploaded.getvalue()
        st.session_state.source_bytes = img_bytes
        st.session_state.generated = []
        st.session_state.analysis = None

        with st.spinner("☁️ Uploading to Fal.ai..."):
            try: st.session_state.fal_url = fal_upload(fal_key, img_bytes)
            except Exception as e: st.error(f"Upload failed: {e}"); st.stop()

        with st.spinner("🔍 Detecting type & stones with Florence-2..."):
            try:
                caption = str(fal_caption(fal_key, st.session_state.fal_url))
                detected = detect_type_from_caption(caption)
                counts = detect_stone_counts(caption)
                st.session_state.analysis = {"type": detected, "caption": caption}
                st.session_state.stone_counts = counts
            except Exception as e: st.error(f"Detection failed: {e}"); st.stop()

        st.rerun()

    # STEP 2
    if st.session_state.analysis:
        analysis = st.session_state.analysis
        auto_type = analysis["type"]
        caption = analysis.get("caption", "")
        counts = st.session_state.stone_counts

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="detect-box"><div class="detect-type">{TYPE_ICONS.get(auto_type, "💎")} Auto-detected: {auto_type}</div><div class="detect-caption">"{caption[:250]}{"..." if len(caption) > 250 else ""}"</div></div>', unsafe_allow_html=True)

        # Stone counts detected
        st.markdown(f'<div class="stone-counts">🔢 <b>Detected stone counts:</b> Main: {counts["main"]} · Side: {counts["side"]} · Accent: {counts["accent"]} — these will be preserved in edits</div>', unsafe_allow_html=True)

        st.markdown("**Confirm or change the detected type:**")
        jtype = st.selectbox(label="Jewelry type", options=VALID_TYPES, index=VALID_TYPES.index(auto_type),
            format_func=lambda x: f"{TYPE_ICONS.get(x, '💎')} {x.capitalize()}")

        non_stone = NON_STONE_PARAMS.get(jtype, {})

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Step 2 — Select what to change</p>', unsafe_allow_html=True)

        # --- Non-stone params ---
        st.markdown("**⚙️ Structure / Metal / Detail params:**")
        pnames = list(non_stone.keys())
        half = (len(pnames) + 1) // 2
        c1, c2 = st.columns(2)
        selected_nonstone = []
        for i, pn in enumerate(pnames):
            meta = non_stone[pn]
            col = c1 if i < half else c2
            with col:
                if st.checkbox(label=f"{meta['label']}  ({len(meta['values'])} options)", key=f"cb_{jtype}_{pn}"):
                    selected_nonstone.append(pn)

        # --- Stone params (only for non-statue types) ---
        selected_stones = []
        if jtype in STONE_TYPES:
            st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
            st.markdown("**💎 Diamond stone options:**")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                if st.checkbox(label="💎 Diamond Main (32 sub-options)", key="cb_diamond_main"):
                    selected_stones.append("diamond_main")
            with sc2:
                if st.checkbox(label="💎 Diamond Side (28 sub-options)", key="cb_diamond_side"):
                    selected_stones.append("diamond_side")
            with sc3:
                if st.checkbox(label="💎 Diamond Accent (26 sub-options)", key="cb_diamond_accent"):
                    selected_stones.append("diamond_accent")

            st.markdown("**🔴 Colored stone options:**")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                if st.checkbox(label="🔴 Colored Main (47 sub-options)", key="cb_colored_main"):
                    selected_stones.append("colored_main")
            with cc2:
                if st.checkbox(label="🔵 Colored Side (38 sub-options)", key="cb_colored_side"):
                    selected_stones.append("colored_side")
            with cc3:
                if st.checkbox(label="🟢 Colored Accent (30 sub-options)", key="cb_colored_accent"):
                    selected_stones.append("colored_accent")

        # STEP 3
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Step 3 — Generate variations</p>', unsafe_allow_html=True)

        total_selected = len(selected_nonstone) + len(selected_stones)
        gc1, gc2 = st.columns([1, 2])
        with gc1:
            num = st.select_slider(label="Number of images", options=[5,10,15,20,25,30,35,40,45,50], value=10)
        with gc2:
            mn = get_min_params(num)
            if total_selected < mn:
                st.warning(f"Select at least {mn} param(s) for {num} images. You have {total_selected}.")
            else:
                st.success(f"{total_selected} selected — ready for {num} images")

        can_gen = total_selected >= mn and bool(fal_key) and st.session_state.fal_url is not None

        if st.button("🚀 Generate Variations", type="primary", disabled=not can_gen, use_container_width=True):
            variations = generate_all_variations(jtype, selected_nonstone, selected_stones, num, counts)

            dist = {}
            for v in variations:
                cat = v["label"].split(" → ")[0] if " → " in v["label"] else v["label"]
                dist[cat] = dist.get(cat, 0) + 1
            scols = st.columns(min(len(dist), 5))
            for i, (lb, ct) in enumerate(sorted(dist.items(), key=lambda x: -x[1])):
                if i < 5:
                    with scols[i]: st.metric(label=lb[:20], value=ct)

            with st.expander("📋 Variation plan & edit prompts"):
                for v in variations:
                    st.markdown(f"**{v['index']}.** {v['label']}")
                    st.code(v["prompt"], language=None)

            prog = st.progress(0, text="Starting generation...")
            gen = []
            for i, v in enumerate(variations):
                prog.progress((i+1)/len(variations), text=f"{i+1}/{len(variations)}: {v['label']}")
                try:
                    img_url = fal_edit(fal_key, st.session_state.fal_url, v["prompt"])
                    if img_url:
                        ir = requests.get(img_url, timeout=60)
                        gen.append({"bytes": ir.content, "label": v["label"], "new": v["new"], "url": img_url, "prompt": v["prompt"]})
                except Exception as e:
                    st.warning(f"#{i+1} failed: {e}")
                if i < len(variations)-1: time.sleep(0.5)

            prog.empty()
            st.session_state.generated = gen
            st.success(f"✅ Generated {len(gen)}/{len(variations)} images")

    # STEP 4
    if st.session_state.generated:
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Results</p>', unsafe_allow_html=True)
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
        log = [{"label": i["label"], "new": i["new"], "url": i["url"], "prompt": i["prompt"]} for i in imgs]
        st.download_button(label="📥 Download log (JSON)", data=json.dumps(log, indent=2), file_name="variations_log.json", mime="application/json")

if __name__ == "__main__":
    main()
