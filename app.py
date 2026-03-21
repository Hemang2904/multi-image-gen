# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # ---- SIDEBAR ----
    with st.sidebar:
        st.markdown("## 🔑 Fal.ai API Key")
        # Added .strip() to the input to remove any accidental leading/trailing spaces
        raw_key = st.text_input(
            label="Fal.ai API Key",
            type="password",
            placeholder="Your FAL_KEY...",
            help="https://fal.ai/dashboard/keys",
        )
        fal_key = raw_key.strip() if raw_key else None

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
        st.markdown("• Stone count=0 → won't add stones")
        st.markdown("• Style → only changes metalwork")
        st.markdown("• 4 prompt variants per generation")

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
                # Use the stripped fal_key
                st.session_state.fal_url = fal_upload(fal_key, img_bytes)
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        with st.spinner("🔍 Detecting..."):
            try:
                # Use the stripped fal_key
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
            f'Accent: {counts["accent"]} — preserved in edits. Count=0 means no stones will be added.'
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

        total = len(sel_ns) + len(sel_st)
        gc1, gc2 = st.columns([1, 2])
        with gc1:
            num = st.number_input(
                label="Number of images",
                min_value=5,
                max_value=50,
                value=10,
                step=1,
            )
        with gc2:
            mn = get_min_params(num)
            if total < mn:
                st.warning(
                    f"Select at least {mn} param(s) for {num} images. You have {total}."
                )
            else:
                st.success(f"{total} selected — ready for {num} images")

        can = total >= mn and bool(fal_key) and st.session_state.fal_url

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
                    # Use stripped fal_key
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
