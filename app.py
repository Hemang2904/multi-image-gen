"""
JewelBench — Bulk Jewelry Variation Generator (Streamlit)
==========================================================
Uses ONLY Fal.ai (single API key):
  - Florence-2 Large → image captioning + type detection
  - Flux 2 Turbo Edit → single-component image editing

Edit prompt style:
  "In the provided image of a ring, change the shank from knife-edge
   to split-shank. Do not change anything else in the image."

RUN:
  pip install streamlit fal-client Pillow requests
  streamlit run jewelbench_streamlit.py
"""

import streamlit as st
import os
import json
import random
import base64
import time
import re
import requests
from typing import Dict, List, Optional

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
    .stApp { background-color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #F8FAFC; }

    .main-header {
        background: linear-gradient(135deg, #1B3A5C 0%, #2E75B6 100%);
        padding: 24px 32px; border-radius: 12px; margin-bottom: 24px;
    }
    .main-header h1 { color: white !important; font-size: 28px !important; font-weight: 600 !important; margin: 0 !important; }
    .main-header p { color: rgba(255,255,255,0.8) !important; font-size: 14px !important; margin: 4px 0 0 0 !important; }

    .section-title { font-size: 18px; font-weight: 600; color: #1B3A5C; margin: 0 0 4px 0; }
    .section-sub { font-size: 13px; color: #64748B; margin: 0 0 16px 0; }

    .param-count { display: inline-block; background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }

    .detect-box { background: #F0F7FF; border: 2px solid #2E75B6; border-radius: 12px; padding: 20px 24px; margin: 16px 0; }
    .detect-type { font-size: 22px; font-weight: 700; color: #1B3A5C; text-transform: capitalize; }
    .detect-sub { font-size: 13px; color: #64748B; margin-top: 6px; line-height: 1.5; }

    .card-success { background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 12px; padding: 14px 20px; margin-bottom: 12px; }
    .blue-divider { height: 3px; background: linear-gradient(90deg, #2E75B6, transparent); border: none; border-radius: 2px; margin: 24px 0; }

    .stat-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; text-align: center; }
    .stat-num { font-size: 28px; font-weight: 700; color: #2E75B6; margin: 0; }
    .stat-label { font-size: 12px; color: #94A3B8; margin: 0; }

    .min-warn { background: #FEF3C7; border: 1px solid #FCD34D; border-radius: 8px; padding: 8px 14px; font-size: 13px; color: #92400E; }
    .var-change { font-size: 11px; color: #2E75B6; font-weight: 600; }
    .var-label { font-size: 11px; color: #64748B; }

    .prompt-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #475569; font-family: monospace; margin: 4px 0 12px 0; line-height: 1.5; }

    .stProgress > div > div > div > div { background-color: #2E75B6; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# PARAMS
# ============================================================================
MIN_PARAMS_RULES = {10: 1, 20: 2, 30: 2, 40: 3, 50: 4}
def get_min_params(n):
    for t in sorted(MIN_PARAMS_RULES.keys(), reverse=True):
        if n >= t: return MIN_PARAMS_RULES[t]
    return 1

TYPE_ICONS = {"ring": "💍", "pendant": "📿", "earring": "✨", "bangle": "⭕", "necklace": "📿", "bracelet": "⛓️", "statue": "🗿"}
VALID_TYPES = ["ring", "pendant", "earring", "bangle", "necklace", "bracelet", "statue"]

ESSENTIAL_PARAMS = {
    "ring": {
        "shank_style":      {"label": "Shank style",   "values": ["knife-edge","tapered","comfort-fit rounded","flat band","euro-shank","split-shank","twisted rope","bypass-swirl","open lattice","cathedral shank","double-rail","scalloped gallery shank","architectural ribbed","bamboo textured","braided wire"]},
        "head_type":        {"label": "Head type",      "values": ["basket mount","cathedral","bezel frame","low-profile flush","tulip head","crown head","suspended crown","tension bridge","geometric frame","double halo head","raised pedestal","lotus head","trellis/lattice head","compass prong head","split-claw head"]},
        "setting_type":     {"label": "Stone setting",  "values": ["4-prong claw","6-prong claw","full bezel","half bezel","tension set","channel set","micro pave","bar set","gypsy/flush set","invisible set","cathedral bezel","collet set"]},
        "stone_shape":      {"label": "Stone shape",    "values": ["round brilliant","princess cut","oval","emerald cut","cushion","pear"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","14K yellow gold","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "side_stone_style": {"label": "Side stones",    "values": ["none","pave band","channel-set baguettes","bezel-set rounds"]},
        "shoulder_style":   {"label": "Shoulder style", "values": ["plain","pave-set","tapered baguette","milgrain edged"]},
        "gallery_style":    {"label": "Gallery",        "values": ["open gallery","closed gallery","filigree gallery","hidden halo gallery","pierced gallery","scroll gallery","lattice gallery","crown gallery"]},
        "edge_finish":      {"label": "Edge finish",    "values": ["plain","milgrain","rope edge","knife edge"]},
    },
    "pendant": {
        "pendant_shape":    {"label": "Pendant shape",  "values": ["round","oval","teardrop","heart","bar","disc","geometric hexagon","marquise silhouette","cross","star","crescent moon","kite/rhombus","shield","pear drop","octagon"]},
        "frame_style":      {"label": "Frame style",    "values": ["open frame","closed back","halo frame","minimal wire frame","double frame","vintage scroll frame","art deco geometric frame","floating/tension frame","cage/lantern frame","bezel wrap frame"]},
        "bail_type":        {"label": "Bail type",      "values": ["fixed bail","hidden bail","tube bail","diamond-set bail","split bail","rabbit ear bail","enhancer clip bail","hinged bail","omega bail","double loop bail"]},
        "setting_type":     {"label": "Stone setting",  "values": ["prong set","bezel set","tension set","pave set","flush set"]},
        "stone_shape":      {"label": "Stone shape",    "values": ["round brilliant","oval","emerald cut","cushion","pear","cabochon"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "border_detail":    {"label": "Border detail",  "values": ["none","milgrain border","rope border","scalloped edge"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","celestial star/moon","infinity symbol"]},
        "layer_dimension":  {"label": "Dimension",      "values": ["flat single layer","domed","concave dish","multi-layer stacked"]},
    },
    "earring": {
        "earring_type":     {"label": "Earring type",   "values": ["stud","drop","hoop","huggie","chandelier","climber","threader","ear cuff","jacket","dangle","crawler","front-back (peek-a-boo)","shield/disc"]},
        "silhouette_shape": {"label": "Silhouette",     "values": ["round","oval","teardrop","geometric angular","linear bar","fan/semicircle","floral cluster","abstract organic","kite/diamond","starburst","crescent","triangular","cascading tier"]},
        "closure_type":     {"label": "Closure type",   "values": ["push back","screw back","lever back","hook/shepherd","hinged","latch back","snap post","omega clip","threader chain","ear wire with bead stop"]},
        "frame_style":      {"label": "Frame style",    "values": ["open","closed","filigree","wire wrap","sculpted solid","cage/lantern","lattice","halo surround","art deco geometric","floating/tension"]},
        "setting_type":     {"label": "Stone setting",  "values": ["prong set","bezel set","channel set","pave set","flush set"]},
        "stone_shape":      {"label": "Stone shape",    "values": ["round brilliant","princess cut","oval","cushion","pear"]},
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
        "stone_arrangement":{"label": "Stones",         "values": ["none","single center stone","half-way set","station-set evenly spaced"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","celestial","geometric"]},
    },
    "necklace": {
        "necklace_type":    {"label": "Necklace type",  "values": ["chain","pendant chain","choker","station necklace","lariat/Y-chain","collar","multi-strand","statement bib","rivière","omega","festoon","rope length","layered set"]},
        "chain_style":      {"label": "Chain style",    "values": ["cable link","box chain","curb link","rope chain","figaro","snake chain","Singapore twist","wheat chain","paperclip link","ball/bead chain","Byzantine","Venetian box","herringbone flat","mariner/anchor"]},
        "pendant_element":  {"label": "Pendant element","values": ["none (chain only)","solitaire drop","bar pendant","disc/coin","initial letter","locket","cross","gemstone cluster","geometric charm","medallion","tassel drop","heart silhouette"]},
        "link_shape":       {"label": "Link shape",     "values": ["round","oval","elongated rectangle","flat disc","N/A (solid chain)","textured nugget","twisted figure-8","marquise link","heart link","hammered organic","graduated sizing"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","diamond-cut faceted"]},
        "clasp_type":       {"label": "Clasp type",     "values": ["lobster claw","spring ring","toggle","box clasp","magnetic"]},
        "surface_texture":  {"label": "Surface texture","values": ["smooth","hammered links","twisted links","diamond-cut facets"]},
        "chain_thickness":  {"label": "Thickness",      "values": ["delicate (0.5-1mm)","thin (1-1.5mm)","medium (2-3mm)","thick (4-5mm)"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","celestial","geometric","infinity"]},
    },
    "bracelet": {
        "bracelet_type":    {"label": "Bracelet type",  "values": ["chain link","tennis","cuff","charm","bar/ID","mesh","bangle style","wrap","beaded","hinged segment","serpenti/snake","sliding/bolo","station"]},
        "link_style":       {"label": "Link style",     "values": ["cable","curb","figaro","rope","box","N/A (solid)","Byzantine","Cuban","paperclip","mariner/anchor","wheat","herringbone","Venetian"]},
        "closure_type":     {"label": "Closure type",   "values": ["lobster claw","toggle","box clasp","fold-over","magnetic"]},
        "metal_type":       {"label": "Metal type",     "values": ["18K yellow gold","18K white gold","18K rose gold","platinum","sterling silver"]},
        "metal_finish":     {"label": "Metal finish",   "values": ["high polish","brushed matte","satin","hammered"]},
        "surface_texture":  {"label": "Surface texture","values": ["smooth","hammered","twisted cable","braided","diamond-cut","bark texture","granulated","brushed linear","woven mesh","filigree overlay","satin matte","sandblasted"]},
        "band_width":       {"label": "Band width",     "values": ["delicate (1-2mm)","thin (3-4mm)","medium (5-7mm)","wide (8-12mm)"]},
        "stone_arrangement":{"label": "Stones",         "values": ["none","single center","half-way around","full eternity","station-set spaced"]},
        "edge_treatment":   {"label": "Edge treatment", "values": ["plain","milgrain","rope border","scalloped"]},
        "motif":            {"label": "Motif",          "values": ["none","floral","geometric","celestial"]},
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

COMPONENT_NAMES = {
    "shank_style": "shank", "head_type": "head/crown", "setting_type": "stone setting",
    "stone_shape": "center stone shape", "metal_type": "metal", "metal_finish": "metal finish/surface",
    "side_stone_style": "side stones", "shoulder_style": "shoulders", "gallery_style": "gallery",
    "edge_finish": "edge finish", "pendant_shape": "pendant shape", "frame_style": "frame",
    "bail_type": "bail", "border_detail": "border", "motif": "decorative motif",
    "layer_dimension": "depth/dimension", "earring_type": "earring type", "silhouette_shape": "silhouette shape",
    "closure_type": "closure/back", "drop_length": "drop length", "bangle_type": "bangle form",
    "cross_section": "cross-section profile", "band_width": "band width", "surface_pattern": "surface pattern",
    "edge_treatment": "edge treatment", "stone_arrangement": "stone arrangement",
    "necklace_type": "necklace style", "chain_style": "chain link style", "pendant_element": "pendant element",
    "link_shape": "link shape", "clasp_type": "clasp", "surface_texture": "surface texture",
    "chain_thickness": "chain thickness", "bracelet_type": "bracelet style", "link_style": "link style",
    "pose": "pose", "proportion": "body proportions", "surface_detail": "surface detail level",
    "theme": "artistic theme", "base_type": "base/pedestal", "base_material": "base material",
    "clothing_drape": "clothing/draping", "texture_contrast": "texture contrast",
}


# ============================================================================
# FAL.AI — Single key for everything
# ============================================================================

def fal_upload(fal_key: str, img_bytes: bytes) -> str:
    """Upload image to fal.ai storage."""
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    return fal_client.upload(img_bytes, "image/png")


def fal_caption(fal_key: str, image_url: str) -> str:
    """Use Florence-2 on fal.ai to caption the image for type detection."""
    import fal_client
    os.environ["FAL_KEY"] = fal_key
    result = fal_client.subscribe(
        "fal-ai/florence-2-large/more-detailed-caption",
        arguments={"image_url": image_url},
    )
    if isinstance(result, dict):
        return result.get("results", "")
    return str(result)


def detect_type_from_caption(caption: str) -> str:
    """Parse Florence-2 caption to detect jewelry type."""
    caption_lower = caption.lower()

    # Priority order — most specific first
    type_keywords = {
        "earring":  ["earring", "ear ring", "stud", "hoop earring", "dangle"],
        "bangle":   ["bangle", "cuff bracelet", "cuff"],
        "bracelet": ["bracelet", "wristband", "chain link bracelet", "tennis bracelet"],
        "necklace": ["necklace", "chain", "choker", "pendant chain"],
        "pendant":  ["pendant", "locket", "charm necklace"],
        "ring":     ["ring", "band", "solitaire", "engagement"],
        "statue":   ["statue", "figurine", "sculpture", "figure", "bust"],
    }

    for jtype, keywords in type_keywords.items():
        for kw in keywords:
            if kw in caption_lower:
                return jtype

    return "ring"  # Default fallback


def fal_edit(fal_key: str, source_url: str, prompt: str) -> Optional[str]:
    """Call Flux 2 Turbo Edit — edit image with prompt."""
    import fal_client
    os.environ["FAL_KEY"] = fal_key

    result = fal_client.subscribe(
        "fal-ai/flux-2/turbo/edit",
        arguments={
            "image_urls": [source_url],
            "prompt": prompt,
            "num_images": 1,
            "num_inference_steps": 6,
            "guidance_scale": 25,
        },
    )
    if isinstance(result, dict):
        images = result.get("images", [])
        if images and isinstance(images[0], dict):
            return images[0].get("url")
    return None


# ============================================================================
# EDIT PROMPT BUILDER
# ============================================================================

def build_edit_prompt(jewelry_type: str, param: str, new_value: str) -> str:
    """
    Edit-focused prompt — tells Flux to change ONLY one component.
    Does NOT reference old value (Flux doesn't know what's current, it sees the image).
    """
    component = COMPONENT_NAMES.get(param, param.replace("_", " "))

    return (
        f"In the provided image of a {jewelry_type}, change the {component} "
        f"to a {new_value}. "
        f"Do not change anything else in the image. "
        f"Keep the same angle, lighting, background, proportions, and overall design. "
        f"Only modify the {component}."
    )


# ============================================================================
# VARIATION GENERATOR
# ============================================================================

def generate_variations(jtype, selected, num):
    essential = ESSENTIAL_PARAMS[jtype]
    variations, used, idx, att = [], set(), 0, 0

    while len(variations) < num and att < num * 10:
        att += 1
        p = selected[idx % len(selected)]
        idx += 1
        vals = essential[p]["values"]
        nv = random.choice(vals)
        key = (p, nv)
        if key in used and att < num * 3:
            continue
        used.add(key)

        prompt = build_edit_prompt(jtype, p, nv)
        variations.append({
            "index": len(variations) + 1,
            "prompt": prompt,
            "param": p,
            "label": essential[p]["label"],
            "new": nv,
        })
    return variations


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # ---- SIDEBAR ----
    with st.sidebar:
        st.markdown("### 🔑 Fal.ai API Key")
        st.markdown("One key for everything — detection + generation.")
        fal_key = st.text_input(
            label="Fal.ai API Key",
            type="password",
            placeholder="Your FAL_KEY...",
            help="Get from https://fal.ai/dashboard/keys",
        )

        if fal_key:
            st.success("API key set", icon="✅")
        else:
            st.warning("API key required", icon="⚠️")

        st.markdown("---")
        st.markdown("### 📖 How it works")
        st.markdown(
            "**1 API key, 2 models:**\n\n"
            "🔍 **Florence-2** — detects jewelry type from image\n\n"
            "🎨 **Flux 2 Edit** — generates single-component edits\n\n"
            "Each variation uses an edit prompt:\n\n"
            '*"In the provided image, change the shank to split-shank. '
            'Do not change anything else."*'
        )
        st.markdown("---")
        st.markdown("### 📊 Min params required")
        st.markdown("| Images | Min |\n|--------|-----|\n| 10 | 1 |\n| 20–30 | 2 |\n| 40 | 3 |\n| 50 | 4 |")

    # ---- HEADER ----
    st.markdown(
        '<div class="main-header">'
        '<h1>💎 JewelBench — Bulk Variation Generator</h1>'
        '<p>Upload → detect → select components → generate precise single-edit variations — all via Fal.ai</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- SESSION STATE ----
    for k, d in [("analysis", None), ("source_bytes", None), ("fal_url", None),
                 ("generated", []), ("caption", None)]:
        if k not in st.session_state:
            st.session_state[k] = d

    # ================================================================
    # STEP 1: Upload + Analyze
    # ================================================================
    st.markdown('<p class="section-title">Step 1 — Upload source image</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Upload a jewelry photo. Florence-2 will detect the type, then you confirm and select what to change.</p>', unsafe_allow_html=True)

    col_up, col_prev = st.columns([1, 1])

    with col_up:
        uploaded = st.file_uploader(
            label="Upload jewelry image",
            type=["png", "jpg", "jpeg", "webp"],
            label_visibility="collapsed",
        )

    with col_prev:
        if uploaded is not None:
            st.image(uploaded, caption="Source image", width=280)
        elif st.session_state.source_bytes is not None:
            st.image(st.session_state.source_bytes, caption="Source image", width=280)

    if not fal_key:
        st.info("👈 Enter your Fal.ai API key in the sidebar to get started.")

    # Analyze button
    can_analyze = uploaded is not None and bool(fal_key)
    if st.button("🔍 Analyze Image", type="primary", disabled=not can_analyze):
        img_bytes = uploaded.getvalue()
        st.session_state.source_bytes = img_bytes
        st.session_state.generated = []
        st.session_state.analysis = None

        # Upload to fal.ai
        with st.spinner("☁️ Uploading image to Fal.ai..."):
            try:
                fal_url = fal_upload(fal_key, img_bytes)
                st.session_state.fal_url = fal_url
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        # Detect type with Florence-2
        with st.spinner("🔍 Detecting jewelry type with Florence-2..."):
            try:
                caption = fal_caption(fal_key, fal_url)
                st.session_state.caption = str(caption)
                detected_type = detect_type_from_caption(str(caption))
                st.session_state.analysis = {"type": detected_type, "caption": str(caption)}
            except Exception as e:
                st.error(f"Detection failed: {e}")
                st.stop()

        st.rerun()

    # ================================================================
    # STEP 2: Confirm type + Select params
    # ================================================================
    if st.session_state.analysis:
        analysis = st.session_state.analysis
        auto_type = analysis["type"]
        caption = analysis.get("caption", "")

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)

        # Detection result with type override
        st.markdown(
            f'<div class="detect-box">'
            f'<span class="detect-type">{TYPE_ICONS.get(auto_type, "💎")} Auto-detected: {auto_type}</span>'
            f'<div class="detect-sub">Florence-2 caption: <em>"{caption[:200]}{"..." if len(caption) > 200 else ""}"</em></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Let user override type if detection is wrong
        jtype = st.selectbox(
            label="Confirm or change jewelry type",
            options=VALID_TYPES,
            index=VALID_TYPES.index(auto_type),
            format_func=lambda x: f"{TYPE_ICONS.get(x, '💎')} {x.capitalize()}",
        )

        essential = ESSENTIAL_PARAMS[jtype]

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Step 2 — Select what to change</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-sub">Tick components to vary. Each generates an edit like: '
            '<em>"In the provided image, change the shank to split-shank. Do not change anything else."</em></p>',
            unsafe_allow_html=True,
        )

        pnames = list(essential.keys())
        half = (len(pnames) + 1) // 2
        c1, c2 = st.columns(2)
        selected = []

        for i, pn in enumerate(pnames):
            meta = essential[pn]
            col = c1 if i < half else c2
            with col:
                if st.checkbox(meta["label"], key=f"cb_{jtype}_{pn}"):
                    selected.append(pn)
                st.markdown(
                    f'<span class="param-count">{len(meta["values"])} options</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ============================================================
        # STEP 3: Generate
        # ============================================================
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Step 3 — Generate variations</p>', unsafe_allow_html=True)

        gc1, gc2 = st.columns([1, 2])
        with gc1:
            num = st.select_slider(
                label="Number of images",
                options=[10, 20, 30, 40, 50],
                value=10,
            )
        with gc2:
            mn = get_min_params(num)
            if len(selected) < mn:
                st.markdown(
                    f'<div class="min-warn">⚠️ Select at least <b>{mn}</b> param(s) for {num} images. You have <b>{len(selected)}</b>.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="card-success">✓ <b>{len(selected)}</b> selected — ready for <b>{num}</b> images</div>',
                    unsafe_allow_html=True,
                )

        can_gen = len(selected) >= mn and bool(fal_key) and st.session_state.fal_url is not None

        if st.button("🚀 Generate Variations", type="primary", disabled=not can_gen, use_container_width=True):
            variations = generate_variations(jtype, selected, num)

            # Stats
            dist = {}
            for v in variations:
                dist[v["label"]] = dist.get(v["label"], 0) + 1
            scols = st.columns(min(len(dist), 5))
            for i, (lb, ct) in enumerate(sorted(dist.items(), key=lambda x: -x[1])):
                if i < 5:
                    with scols[i]:
                        st.markdown(
                            f'<div class="stat-box"><p class="stat-num">{ct}</p><p class="stat-label">{lb}</p></div>',
                            unsafe_allow_html=True,
                        )

            # Plan with prompts
            with st.expander("📋 Variation plan & edit prompts"):
                for v in variations:
                    st.markdown(f"**{v['index']}.** [{v['label']}] → `{v['new']}`")
                    st.markdown(f'<div class="prompt-box">{v["prompt"]}</div>', unsafe_allow_html=True)

            # Generate
            prog = st.progress(0, text="Starting generation...")
            gen = []

            for i, v in enumerate(variations):
                prog.progress(
                    (i + 1) / len(variations),
                    text=f"{i + 1}/{len(variations)}: {v['label']} → {v['new']}",
                )
                try:
                    img_url = fal_edit(fal_key, st.session_state.fal_url, v["prompt"])
                    if img_url:
                        img_resp = requests.get(img_url, timeout=60)
                        gen.append({
                            "bytes": img_resp.content,
                            "label": v["label"],
                            "new": v["new"],
                            "url": img_url,
                            "prompt": v["prompt"],
                        })
                except Exception as e:
                    st.warning(f"#{i + 1} failed: {e}")

                if i < len(variations) - 1:
                    time.sleep(0.5)

            prog.empty()
            st.session_state.generated = gen
            st.markdown(
                f'<div class="card-success">✅ Generated <b>{len(gen)}/{len(variations)}</b> images</div>',
                unsafe_allow_html=True,
            )

    # ================================================================
    # STEP 4: Results
    # ================================================================
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
                        st.markdown(
                            f'<div style="text-align:center">'
                            f'<span class="var-change">{im["label"]}</span><br>'
                            f'<span class="var-label">→ {im["new"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

        # Download
        log = [{"label": i["label"], "new": i["new"], "url": i["url"], "prompt": i["prompt"]} for i in imgs]
        st.download_button(
            label="📥 Download log with prompts (JSON)",
            data=json.dumps(log, indent=2),
            file_name="variations_log.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
