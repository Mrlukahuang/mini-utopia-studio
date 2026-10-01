from pathlib import Path

import streamlit as st

from studio.core.config import get_settings
from studio.core.enums import AssetType, StoryMode
from studio.models.character import CharacterProfile
from studio.recipes.character_factory import CharacterFactoryRecipe
from studio.services.bootstrap import build_context
from studio.ui.auth import lock_studio, require_studio_pin

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="Mini Utopia Studio",
    page_icon="✨",
    layout="wide",
)

ctx = build_context(get_settings(ROOT))
universe = ctx.universes.ensure_mini_utopia()
character_factory = CharacterFactoryRecipe(ctx.registry, ctx.assets)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    .stButton > button {
        border-radius: 16px;
        min-height: 2.8rem;
        font-weight: 650;
    }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,.94);
        border: 1px solid rgba(108,92,231,.14);
        padding: 16px;
        border-radius: 20px;
        box-shadow: 0 8px 30px rgba(38,32,72,.06);
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #20243a !important;
    }
    .mu-hero {
        padding: 28px 30px;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,244,208,.96), rgba(236,245,255,.96));
        border: 1px solid rgba(108,92,231,.10);
        margin-bottom: 22px;
    }
    .mu-hero h1 {
        color: #25233b;
        margin: 0 0 8px 0;
        font-size: 2.35rem;
        line-height: 1.12;
    }
    .mu-hero p {
        color: #55546b;
        font-size: 1.05rem;
        margin: 0;
    }
    .mu-note {
        padding: 16px 18px;
        border-radius: 18px;
        background: rgba(226,245,255,.72);
        border: 1px solid rgba(43,143,216,.12);
        color: #23415c;
    }
    .mu-pill {
        display: inline-block;
        padding: 5px 10px;
        margin-right: 6px;
        margin-bottom: 6px;
        border-radius: 999px;
        background: rgba(108,92,231,.10);
        color: #5b50be;
        font-size: .85rem;
        font-weight: 600;
    }
    div[data-testid="stSidebar"] {
        border-right: 1px solid rgba(125,125,145,.12);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None

st.title("✨ Mini Utopia · AI Creative Studio")

mode = st.sidebar.radio(
    "Mode",
    ["🧒 Creator", "🛠 Studio"],
    key="app_mode",
)

page = st.sidebar.radio(
    "Create",
    [
        "🏠 Home",
        "🎭 My Characters",
        "✨ Character Factory",
        "🌎 Mini Utopia",
        "🧪 Playground",
        "📖 Stories",
    ],
    key="app_page",
)

if page == "🏠 Home":
    st.markdown(
        """<div class="mu-hero">
<div class="mu-cloud">☁️</div>
<h1>Small Worlds. Big Imagination. ✨</h1>
<div class="mu-signature">❤️✨ Charlotte & Chelsea ✨❤️ 的 Utopia (乌托邦) ✨☁️</div>
<p>Create a character once, keep it forever, and take it anywhere. Today Auckland. Tomorrow the Moon. Next week — who knows?</p>
</div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎭 Characters", len(ctx.repository.list_assets(AssetType.CHARACTER)))
    c2.metric("🌍 Places", len(ctx.repository.list_assets(AssetType.LOCATION)))
    c3.metric("🎒 Objects", len(ctx.repository.list_assets(AssetType.PROP)))
    c4.metric("📖 Stories", len(ctx.repository.list_stories()))

    st.markdown(
        """
        <div class="mu-note">
            <b>Creative LEGO:</b> 角色、地点、道具和风格都是独立资产。Story 只负责把它们自由组合。
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.subheader("Where should we create today?")
    a, b, c = st.columns(3)
    with a:
        st.markdown("### 🎭 Character")
        st.caption("创造一个可以反复使用的角色。")
    with b:
        st.markdown("### 🌍 Mini World")
        st.caption("创造一个新的地点、星球或奇怪世界。")
    with c:
        st.markdown("### 🧪 Playground")
        st.caption("No rules. No canon. Just create.")

elif page == "🎭 My Characters":
    st.header("🎭 My Characters")
    chars = ctx.repository.list_assets(AssetType.CHARACTER)

    if not chars:
        st.info("还没有角色。去 Character Factory 创造第一个 Traveler 吧！")

    for asset in chars:
        with st.container(border=True):
            st.subheader(asset.display_name)
            st.caption(asset.asset_id)
            st.write(asset.description or "等待描述")
            profile = asset.metadata.get("character_profile", {})
            personality = profile.get("personality", [])
            if personality:
                st.markdown(
                    "".join(f'<span class="mu-pill">{item}</span>' for item in personality),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("等待性格设定")

elif page == "✨ Character Factory":
    st.header("✨ Create Our Traveler")
    st.write("先像讲故事一样描述。AI 会把想法拆成维度；你仍然拥有最后决定权。")

    description = st.text_area(
        "你想创造谁？",
        placeholder="例如：一只胖胖的大熊猫，戴黄色帽子，穿蓝色背带裤。他有点胆小，但特别喜欢冒险。",
        height=130,
    )

    if st.button("✨ Help Me Understand", type="primary", disabled=not description.strip()):
        st.session_state.char_source = description
        st.session_state.char_draft = character_factory.parse_description(description)

    draft: CharacterProfile | None = st.session_state.char_draft

    if draft:
        st.divider()
        st.subheader("🧩 我理解的角色")
        name = st.text_input("名字", placeholder="可以现在取，也可以以后改")
        c1, c2 = st.columns(2)

        with c1:
            species = st.text_input("物种 / 类型", value=draft.species)
            body = st.text_input("身体特征", value=draft.body)
            face = st.text_input("脸部特征", value=draft.face)
            clothing = st.text_input("服装", value=draft.clothing)

        with c2:
            personality = st.text_input("性格（逗号分隔）", value="，".join(draft.personality))
            strengths = st.text_input("擅长", value="，".join(draft.strengths))
            weaknesses = st.text_input("弱点", value="，".join(draft.weaknesses))
            immutable = st.text_input("以后不能随便改变的特征", value="，".join(draft.immutable_features))

        if st.button("❤️ Save This Character", type="primary", disabled=not name.strip()):
            def split_items(value: str) -> list[str]:
                return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]

            final_profile = draft.model_copy(
                update={
                    "species": species,
                    "body": body,
                    "face": face,
                    "clothing": clothing,
                    "personality": split_items(personality),
                    "strengths": split_items(strengths),
                    "weaknesses": split_items(weaknesses),
                    "immutable_features": split_items(immutable),
                }
            )

            asset = character_factory.save_character(
                name=name,
                description=st.session_state.get("char_source", ""),
                profile=final_profile,
            )

            st.success(f"保存成功：{asset.display_name} · {asset.asset_id}")
            st.session_state.char_draft = None
            st.caption("下一阶段会把 Master Reference、Front / Side / Back、表情、姿势都挂在这个 CHAR_ID 下。")

elif page == "🌎 Mini Utopia":
    st.header("🌎 Mini Utopia")
    st.subheader(universe.tagline)
    st.write(universe.description)
    st.markdown("**Story Formula** · " + " → ".join(universe.story_formula))
    st.markdown("**Portal Rule** · " + universe.portal_rule)
    st.markdown("**Canon Rules**")
    for rule in universe.canon_rules:
        st.write("✓ " + rule)

    if universe.traveler_asset_id:
        traveler = ctx.repository.get_asset(universe.traveler_asset_id)
        st.success(f"Current Traveler: {traveler.display_name if traveler else universe.traveler_asset_id}")
    else:
        st.caption("Traveler 尚未锁定。确认第一个 Character Master 后再设为 Mini Utopia Traveler。")

elif page == "🧪 Playground":
    st.header("🧪 Playground")
    st.write("No rules. No canon. Just create. 这里的实验不会自动改变 Mini Utopia。")
    title = st.text_input("给这个疯狂想法一个名字")
    premise = st.text_area("发生什么？", placeholder="例如：写实恐龙和水彩香蕉在学校打篮球……")
    chars = ctx.repository.list_assets(AssetType.CHARACTER)
    selected = st.multiselect("想带上哪些已有角色？", chars, format_func=lambda asset: asset.display_name)

    if st.button("Save Playground Story", disabled=not title or not premise):
        story = ctx.stories.create_story(
            title=title,
            premise=premise,
            mode=StoryMode.PLAYGROUND,
            asset_ids=[asset.asset_id for asset in selected],
        )
        st.success(f"已保存：{story.story_id}")

elif page == "📖 Stories":
    st.header("📖 Stories")
    stories = ctx.repository.list_stories()

    if not stories:
        st.info("还没有 Story。可以先在 Playground 保存一个疯狂想法。")

    for story in stories:
        with st.container(border=True):
            st.subheader(story.title)
            st.caption(f"{story.story_id} · {story.mode.value}")
            st.write(story.premise)
            st.caption("Assets: " + (", ".join(story.asset_ids) or "none"))

if mode == "🛠 Studio":
    st.sidebar.divider()

    if require_studio_pin():
        st.sidebar.success("Studio unlocked")
        st.sidebar.caption("Foundation v0.3")
        st.sidebar.caption("Capabilities: " + ", ".join(ctx.registry.list_capabilities()))

        if st.sidebar.button("🔒 Lock Studio", use_container_width=True):
            lock_studio()

        with st.expander("🛠 Studio Inspector", expanded=True):
            st.write("Universe")
            st.json(universe.model_dump(mode="json"))
            st.write("Assets")
            st.json([asset.model_dump(mode="json") for asset in ctx.repository.list_assets()])
            st.write("Jobs")
            st.json([job.model_dump(mode="json") for job in ctx.repository.list_jobs()])
    else:
        st.sidebar.caption("Studio is locked.")
