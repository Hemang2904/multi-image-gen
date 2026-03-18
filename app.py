"""
JewelBench — Bulk Jewelry Variation Generator (Streamlit)
==========================================================
Clean white + blue UI. Upload image → auto-detect type → select params → generate.

RUN:
  pip install streamlit fal-client openai Pillow requests
  streamlit run jewelbench_streamlit.py
"""

import streamlit as st
import os
import json
import random
import base64
import time
import requests
import io
from typing import Dict, List, Optional
from pathlib import Path

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="JewelBench — Bulk Variations",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# CUSTOM CSS — White background, blue accents
# ============================================================================
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #F8FAFC; }

    /* Header bar */
    .main-header {
        background: linear-gradient(135deg, #1B3A5C 0%, #2E75B6 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .main-header h1 {
        color: white !important;
        font-size: 28px !important;
        font-weight: 600 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .main-header p {
        color: rgba(255,255,255,0.8) !important;
        font-size: 14px !important;
        margin: 4px 0 0 0 !important;
    }

    /* Cards */
    .card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .card-blue {
        background: #F0F7FF;
        border: 1px solid #B5D4F4;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .card-success {
        background: #F0FDF4;
        border: 1px solid #86EFAC;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }

    /* Section titles */
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #1B3A5C;
        margin: 0 0 4px 0;
    }
    .section-sub {
        font-size: 13px;
        color: #64748B;
        margin: 0 0 16px 0;
    }

    /* Param chips */
    .param-current {
        display: inline-block;
        background: #F1F5F9;
        color: #475569;
        padding: 2px 10px;
        border-radius: 6px;
        font-size: 12px;
        margin-left: 4px;
    }
    .param-count {
        display: inline-block;
        background: #DBEAFE;
        color: #1E40AF;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 4px;
    }

    /* Variation card */
    .var-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 8px;
        text-align: center;
        transition: all 0.2s;
    }
    .var-card:hover {
        border-color: #2E75B6;
        box-shadow: 0 4px 12px rgba(46,117,182,0.15);
    }
    .var-label {
        font-size: 11px;
        color: #64748B;
        margin-top: 6px;
        line-height: 1.3;
    }
    .var-change {
        font-size: 11px;
        color: #2E75B6;
        font-weight: 600;
    }

    /* Detection popup */
    .detect-box {
        background: #F0F7FF;
        border: 2px solid #2E75B6;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 16px 0;
    }
    .detect-type {
        font-size: 24px;
        font-weight: 700;
        color: #1B3A5C;
        text-transform: capitalize;
    }
    .detect-sub {
        font-size: 14px;
        color: #64748B;
    }

    /* Progress */
    .stProgress > div > div > div > div {
        background-color: #2E75B6;
    }

    /* Buttons */
    .stButton > button {
        background-color: #2E75B6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background-color: #1B3A5C !important;
        box-shadow: 0 4px 12px rgba(27,58,92,0.3) !important;
    }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Checkbox styling */
    .stCheckbox label p { font-size: 14px !important; }

    /* Divider */
    .blue-divider {
        height: 3px;
        background: linear-gradient(90deg, #2E75B6, transparent);
        border: none;
        border-radius: 2px;
        margin: 24px 0;
    }

    /* Stats row */
    .stat-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
    }
    .stat-num {
        font-size: 28px;
        font-weight: 700;
        color: #2E75B6;
        margin: 0;
    }
    .stat-label {
        font-size: 12px;
        color: #94A3B8;
        margin: 0;
    }

    /* Min params warning */
    .min-warn {
        background: #FEF3C7;
        border: 1px solid #FCD34D;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 13px;
        color: #92400E;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# PARAM DATA (expanded high-impact values)
# ============================================================================

MIN_PARAMS_RULES = {10: 1, 20: 2, 30: 2, 40: 3, 50: 4}

def get_min_params(n):
    for t in sorted(MIN_PARAMS_RULES.keys(), reverse=True):
        if n >= t: return MIN_PARAMS_RULES[t]
    return 1

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

# Full params for prompt building (same as essential + non-essential defaults)
# Using essential as full for simplicity — GPT-4o fills all detected values
FULL_PARAMS = {t: {p: m["values"] for p, m in params.items()} for t, params in ESSENTIAL_PARAMS.items()}

BASE_PROMPTS = {
    "ring": "A professional jewelry CAD render of a ring in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. Watertight manifold geometry. No human skin, no props, no branding, no watermark. The ring has: {shank_style} shank, {head_type} head, {setting_type} setting, {stone_shape} stone, {metal_type} with {metal_finish} finish, {side_stone_style} side stones, {shoulder_style} shoulders, {gallery_style}, {edge_finish} edges.",
    "pendant": "A professional jewelry CAD render of a pendant in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. No human skin, no props, no branding, no watermark. The pendant has: {pendant_shape} shape, {bail_type} bail, {setting_type} setting, {stone_shape} stone, {metal_type} with {metal_finish} finish, {frame_style} frame, {border_detail} border, {motif} motif, {layer_dimension} dimension.",
    "earring": "A professional jewelry CAD render of earrings in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. No human skin, no props, no branding, no watermark. The earrings are: {earring_type} type, {closure_type} closure, {setting_type} setting, {stone_shape} stone, {metal_type} with {metal_finish} finish, {silhouette_shape} silhouette, {frame_style} frame, {drop_length} drop, {motif} motif.",
    "bangle": "A professional jewelry CAD render of a bangle in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. No human skin, no props, no branding, no watermark. The bangle has: {bangle_type} type, {cross_section} cross-section, {band_width} width, {closure_type} closure, {metal_type} with {metal_finish} finish, {surface_pattern} surface, {edge_treatment} edges, {stone_arrangement} stones, {motif} motif.",
    "necklace": "A professional jewelry CAD render of a necklace in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. No human skin, no props, no branding, no watermark. The necklace has: {necklace_type} type, {chain_style} chain, {chain_thickness} thickness, {clasp_type} clasp, {metal_type} with {metal_finish} finish, {pendant_element} pendant, {link_shape} links, {surface_texture} texture, {motif} motif.",
    "bracelet": "A professional jewelry CAD render of a bracelet in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp macro detail, 8K resolution. No human skin, no props, no branding, no watermark. The bracelet has: {bracelet_type} type, {link_style} links, {closure_type} closure, {band_width} width, {metal_type} with {metal_finish} finish, {surface_texture} texture, {stone_arrangement} stones, {edge_treatment} edges, {motif} motif.",
    "statue": "A professional 3D render of a decorative metal statue in 3/4 perspective on a neutral #808080 grey background. Ultra-sharp detail, 8K resolution. No branding, no watermark. The statue depicts: {pose} pose, {proportion} proportions, {metal_type} with {metal_finish} finish, {surface_detail} detail, {theme} theme, {base_type} base, {base_material} base material, {clothing_drape} clothing, {texture_contrast} texture.",
}

TYPE_ICONS = {"ring": "💍", "pendant": "📿", "earring": "✨", "bangle": "⭕", "necklace": "📿", "bracelet": "⛓️", "statue": "🗿"}


# ============================================================================
# GPT-4o: Detect type + analyze params
# ============================================================================

def detect_and_analyze(image_bytes: bytes, openai_key: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=openai_key)

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:image/png;base64,{b64}"

    # Step 1: Detect type
    detect_resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Identify the jewelry type in this image. Reply with ONLY one word: ring, pendant, earring, bangle, necklace, bracelet, or statue. Nothing else."},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": "What type of jewelry is this?"}
            ]}
        ],
        max_tokens=10,
        temperature=0.1,
    )
    detected_type = detect_resp.choices[0].message.content.strip().lower().replace(".", "")

    valid_types = list(ESSENTIAL_PARAMS.keys())
    if detected_type not in valid_types:
        for vt in valid_types:
            if vt in detected_type:
                detected_type = vt
                break
        else:
            detected_type = "ring"

    # Step 2: Analyze params
    params = ESSENTIAL_PARAMS[detected_type]
    param_list = ""
    for name, meta in params.items():
        param_list += f"\n  {name}: [{', '.join(meta['values'])}]"

    analyze_resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Analyze this {detected_type} image. For each parameter, pick ONE value from the allowed list. Return ONLY a JSON object. No markdown.\n\nParameters:{param_list}"},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": f"Return JSON with {detected_type} parameter values."}
            ]}
        ],
        max_tokens=1500,
        temperature=0.1,
    )

    raw = analyze_resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
    parsed = json.loads(raw)

    validated = {}
    for name, meta in params.items():
        val = parsed.get(name, meta["values"][0])
        if val not in meta["values"]:
            for v in meta["values"]:
                if v.lower() in val.lower() or val.lower() in v.lower():
                    val = v
                    break
            else:
                val = meta["values"][0]
        validated[name] = val

    return {"type": detected_type, "params": validated}


# ============================================================================
# Variation generator
# ============================================================================

def generate_variations(jewelry_type, current_values, selected_params, num_images):
    essential = ESSENTIAL_PARAMS[jewelry_type]
    variations = []
    used = set()
    idx = 0
    attempts = 0

    while len(variations) < num_images and attempts < num_images * 10:
        attempts += 1
        param = selected_params[idx % len(selected_params)]
        idx += 1
        values = essential[param]["values"]
        curr = current_values.get(param, values[0])
        options = [v for v in values if v != curr]
        if not options:
            continue
        new_val = random.choice(options)
        key = (param, new_val)
        if key in used and attempts < num_images * 3:
            continue
        used.add(key)

        new_values = current_values.copy()
        new_values[param] = new_val
        prompt = BASE_PROMPTS[jewelry_type].format(**new_values)

        variations.append({
            "index": len(variations) + 1,
            "prompt": prompt,
            "param": param,
            "label": essential[param]["label"],
            "old": curr,
            "new": new_val,
        })
    return variations


# ============================================================================
# Fal.ai generation
# ============================================================================

def generate_image_fal(fal_key, source_url, prompt):
    import fal_client
    os.environ["FAL_KEY"] = fal_key

    result = fal_client.subscribe(
        "fal-ai/flux-2/turbo/edit",
        arguments={
            "image_url": source_url,
            "prompt": prompt,
            "num_images": 1,
            "image_size": "1024x1024",
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
# MAIN APP
# ============================================================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>💎 JewelBench — Bulk Variation Generator</h1>
        <p>Upload a jewelry image → select what to change → generate targeted variations</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar for API keys
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        fal_key = st.text_input("Fal.ai API Key", type="password", key="fal_key")
        openai_key = st.text_input("OpenAI API Key", type="password", key="openai_key")
        st.markdown("---")
        st.markdown("**How it works**")
        st.markdown("""
        1. Upload a jewelry image
        2. AI detects the type & components
        3. Select what to vary
        4. Generate 10-50 variations
        """)

    # Initialize session state
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "source_url" not in st.session_state:
        st.session_state.source_url = None
    if "variations" not in st.session_state:
        st.session_state.variations = None
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = []

    # ---- STEP 1: Upload ----
    col_upload, col_preview = st.columns([1, 1])

    with col_upload:
        st.markdown('<p class="section-title">Step 1 — Upload source image</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-sub">Upload a jewelry image or paste a URL</p>', unsafe_allow_html=True)

        upload_tab, url_tab = st.tabs(["📁 Upload file", "🔗 Paste URL"])

        with upload_tab:
            uploaded = st.file_uploader("", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

        with url_tab:
            image_url = st.text_input("Image URL", placeholder="https://...", label_visibility="collapsed")

        # Analyze button
        if st.button("🔍 Analyze Image", use_container_width=True, disabled=not (uploaded or image_url) or not openai_key):
            with st.spinner("Analyzing with GPT-4o Vision..."):
                if uploaded:
                    img_bytes = uploaded.read()
                    st.session_state.source_bytes = img_bytes
                    st.session_state.source_url = None
                else:
                    resp = requests.get(image_url, timeout=30)
                    img_bytes = resp.content
                    st.session_state.source_bytes = img_bytes
                    st.session_state.source_url = image_url

                result = detect_and_analyze(img_bytes, openai_key)
                st.session_state.analysis = result
                st.session_state.variations = None
                st.session_state.generated_images = []
                st.rerun()

    with col_preview:
        if st.session_state.get("source_bytes"):
            st.image(st.session_state.source_bytes, caption="Source image", use_container_width=True)

    # ---- STEP 2: Detection popup + param selection ----
    if st.session_state.analysis:
        analysis = st.session_state.analysis
        jtype = analysis["type"]
        params = analysis["params"]
        essential = ESSENTIAL_PARAMS[jtype]

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)

        # Detection result
        st.markdown(f"""
        <div class="detect-box">
            <span class="detect-type">{TYPE_ICONS.get(jtype, "💎")} Detected: {jtype}</span>
            <span class="detect-sub"> — {len(essential)} adjustable components identified</span>
        </div>
        """, unsafe_allow_html=True)

        # Detected params summary
        st.markdown('<p class="section-title">Step 2 — Select what to change</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-sub">Tick the components you want varied. Each generates a different design twist.</p>', unsafe_allow_html=True)

        # Checkboxes in 2 columns
        param_names = list(essential.keys())
        half = len(param_names) // 2 + len(param_names) % 2
        col1, col2 = st.columns(2)

        selected = []
        for i, pname in enumerate(param_names):
            meta = essential[pname]
            curr_val = params.get(pname, meta["values"][0])
            col = col1 if i < half else col2

            with col:
                checked = st.checkbox(
                    f"{meta['label']}",
                    key=f"cb_{pname}",
                    help=f"Current: {curr_val} | {len(meta['values'])} options available"
                )
                if checked:
                    selected.append(pname)

                st.markdown(
                    f'<span class="param-current">{curr_val}</span> '
                    f'<span class="param-count">{len(meta["values"])} options</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)

        # ---- STEP 3: Count + Generate ----
        st.markdown('<p class="section-title">Step 3 — Generate variations</p>', unsafe_allow_html=True)

        col_count, col_info, col_btn = st.columns([1, 1, 1])

        with col_count:
            num_images = st.select_slider(
                "Number of images",
                options=[10, 20, 30, 40, 50],
                value=10,
            )

        with col_info:
            min_req = get_min_params(num_images)
            if len(selected) < min_req:
                st.markdown(f'<div class="min-warn">⚠️ Select at least <b>{min_req}</b> param(s) for {num_images} images. You have {len(selected)}.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="card-success">✓ <b>{len(selected)}</b> params selected — ready to generate <b>{num_images}</b> images</div>', unsafe_allow_html=True)

        with col_btn:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            can_generate = len(selected) >= min_req and fal_key
            generate_clicked = st.button(
                "🚀 Generate Variations",
                use_container_width=True,
                disabled=not can_generate,
            )

        if not fal_key:
            st.info("Enter your Fal.ai API key in the sidebar to generate images.")

        # ---- Generation ----
        if generate_clicked and can_generate:
            variations = generate_variations(jtype, params, selected, num_images)
            st.session_state.variations = variations

            # Show plan
            with st.expander("📋 Variation plan", expanded=False):
                for v in variations:
                    st.markdown(f"**{v['index']}.** [{v['label']}] `{v['old']}` → `{v['new']}`")

            # Stats
            dist = {}
            for v in variations:
                dist[v["label"]] = dist.get(v["label"], 0) + 1

            stat_cols = st.columns(len(dist))
            for i, (label, count) in enumerate(sorted(dist.items(), key=lambda x: -x[1])):
                with stat_cols[i]:
                    st.markdown(f"""
                    <div class="stat-box">
                        <p class="stat-num">{count}</p>
                        <p class="stat-label">{label}</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # Need a public URL for Fal.ai
            # If user uploaded a file, we need to host it temporarily
            # For now, require URL or use base64 upload to fal
            source_url = st.session_state.get("source_url")
            if not source_url:
                st.warning("For Fal.ai generation, please use an image URL (paste URL tab) instead of file upload, as Fal.ai requires a public URL. Or upload your image to an S3 bucket first.")
                st.stop()

            # Generate images
            progress = st.progress(0, text="Starting generation...")
            generated = []

            for i, v in enumerate(variations):
                progress.progress(
                    (i + 1) / len(variations),
                    text=f"Generating {i+1}/{len(variations)}: {v['label']} → {v['new']}"
                )

                try:
                    img_url = generate_image_fal(fal_key, source_url, v["prompt"])
                    if img_url:
                        img_resp = requests.get(img_url, timeout=60)
                        generated.append({
                            "bytes": img_resp.content,
                            "label": v["label"],
                            "old": v["old"],
                            "new": v["new"],
                            "url": img_url,
                        })
                except Exception as e:
                    st.warning(f"Failed variation {i+1}: {e}")

                if i < len(variations) - 1:
                    time.sleep(0.5)

            progress.empty()
            st.session_state.generated_images = generated

            st.markdown(f'<div class="card-success">✅ Generated <b>{len(generated)}/{len(variations)}</b> images successfully!</div>', unsafe_allow_html=True)

    # ---- STEP 4: Display results ----
    if st.session_state.generated_images:
        st.markdown('<div class="blue-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Results</p>', unsafe_allow_html=True)

        images = st.session_state.generated_images
        cols_per_row = 4
        for row_start in range(0, len(images), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = row_start + j
                if idx < len(images):
                    img = images[idx]
                    with col:
                        st.image(img["bytes"], use_container_width=True)
                        st.markdown(
                            f'<div style="text-align:center;">'
                            f'<span class="var-change">{img["label"]}</span><br>'
                            f'<span class="var-label">{img["old"]} → {img["new"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

        # Download log
        if st.session_state.variations:
            log_data = json.dumps(st.session_state.variations, indent=2)
            st.download_button(
                "📥 Download variation log (JSON)",
                data=log_data,
                file_name="variations_log.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()
