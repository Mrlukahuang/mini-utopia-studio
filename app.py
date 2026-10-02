from pathlib import Path

import streamlit as st

from studio.core.config import get_settings
from studio.core.enums import AssetType, StoryMode
from studio.models.character import CharacterProfile, EyeProfile
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
universe = ctx.styles.attach_base_style(universe)
character_factory = CharacterFactoryRecipe(ctx.registry, ctx.assets)


# ---------------------------------------------------------------------------
# Visual layer
# ---------------------------------------------------------------------------

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
        background: linear-gradient(
            135deg,
            rgba(255,244,208,.96),
            rgba(236,245,255,.96)
        );
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


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None


# ---------------------------------------------------------------------------
# App title
# ---------------------------------------------------------------------------

st.title("❤️✨ Charlotte & Chelsea ✨❤️ 的 Utopia (乌托邦) ✨☁️")


# ---------------------------------------------------------------------------
# Mode selection — IMPORTANT:
# Studio authentication happens BEFORE Studio pages are rendered.
# ---------------------------------------------------------------------------

mode = st.sidebar.radio(
    "Mode",
    ["🧒 Creator", "🛠 Studio"],
    key="app_mode",
)

studio_unlocked = False

if mode == "🛠 Studio":
    st.sidebar.divider()

    studio_unlocked = require_studio_pin()

    if not studio_unlocked:
        st.sidebar.caption("🔒 Studio is locked.")
        st.stop()

    st.sidebar.success("🔓 Studio unlocked")
    st.sidebar.caption("Foundation v0.3")
    st.sidebar.caption(
        "Capabilities: " + ", ".join(ctx.registry.list_capabilities())
    )

    if st.sidebar.button(
        "🔒 Lock Studio",
        use_container_width=True,
    ):
        lock_studio()


# ---------------------------------------------------------------------------
# Page navigation
# Only appears after Studio is authenticated, or immediately in Creator Mode.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Creator / shared pages
# ---------------------------------------------------------------------------

if page == "🏠 Home":
    st.markdown(
        """<div class="mu-hero">
<h1>Small Worlds. Big Imagination. ✨</h1>
<p>Create a character once, keep it forever, and take it anywhere. Today Auckland. Tomorrow the Moon. Next week — who knows?</p>
</div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "🎭 Characters",
        len(ctx.repository.list_assets(AssetType.CHARACTER)),
    )
    c2.metric(
        "🌍 Places",
        len(ctx.repository.list_assets(AssetType.LOCATION)),
    )
    c3.metric(
        "🎒 Objects",
        len(ctx.repository.list_assets(AssetType.PROP)),
    )
    c4.metric(
        "📖 Stories",
        len(ctx.repository.list_stories()),
    )

    st.markdown(
        """
        <div class="mu-note">
            <b>Creative LEGO:</b>
            角色、地点、道具和风格都是独立资产。
            Story 只负责把它们自由组合。
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
        st.info(
            "还没有角色。去 Character Factory 创造第一个 Traveler 吧！"
        )

    for asset in chars:
        with st.container(border=True):
            st.subheader(asset.display_name)
            st.caption(asset.asset_id)
            st.write(asset.description or "等待描述")

            profile = asset.metadata.get("character_profile", {})
            personality = profile.get("personality_traits", [])

            if personality:
                st.markdown(
                    "".join(
                        f'<span class="mu-pill">{item}</span>'
                        for item in personality
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("等待性格设定")


elif page == "✨ Character Factory":
    st.header("✨ Create Our Traveler / 创造角色")
    st.write(
        "先像讲故事一样描述。AI 会帮你整理角色设定；"
        "你可以修改每一个决定。"
    )

    description = st.text_area(
        "你想创造谁？ / Who do you want to create?",
        placeholder=(
            "例如：一只胖胖的大熊猫，戴黄色帽子，穿蓝色背带裤。"
            "他有点胆小，但特别喜欢冒险。"
        ),
        height=130,
    )

    if st.button(
        "✨ Help Me Understand / 帮我整理",
        type="primary",
        disabled=not description.strip(),
    ):
        st.session_state.char_source = description
        st.session_state.char_draft = (
            character_factory.parse_description(description)
        )

    draft: CharacterProfile | None = st.session_state.char_draft

    if draft:
        st.divider()
        st.subheader("⭐ Core / 核心设定")

        def split_items(value: str) -> list[str]:
            return [
                item.strip()
                for item in value.replace("，", ",").split(",")
                if item.strip()
            ]

        name = st.text_input(
            "名字 / Name",
            placeholder="给角色取一个名字",
        )

        c1, c2 = st.columns(2)

        with c1:
            character_type = st.text_input(
                "TA是什么？ / Character Type",
                value=draft.character_type,
                placeholder="例如：人类、大熊猫、机器人、云朵生物",
            )
            age = st.text_input(
                "年龄 / Age",
                value=draft.age,
                placeholder="例如：8、teen、ageless",
            )
            appearance = st.text_input(
                "外形 / Appearance",
                value=draft.appearance,
            )
            hair_or_fur = st.text_input(
                "头发 / 毛发 / Hair or Fur",
                value=draft.hair_or_fur,
            )

            hairstyle_options = [
                "",
                "长直发 / Long straight",
                "长卷发 / Long curly",
                "短发 / Short hair",
                "波波头 / Bob",
                "高马尾 / High ponytail",
                "低马尾 / Low ponytail",
                "双马尾 / Pigtails",
                "丸子头 / Bun",
                "双丸子头 / Double buns",
                "单辫 / Single braid",
                "双辫 / Twin braids",
                "法式辫 / French braid",
                "荷兰辫 / Dutch braid",
                "鱼骨辫 / Fishtail braid",
                "侧辫 / Side braid",
                "皇冠辫 / Crown braid",
                "半扎发 / Half-up",
                "精灵短发 / Pixie cut",
                "其他 / Other",
            ]
            hairstyle_index = (
                hairstyle_options.index(draft.hair_style)
                if draft.hair_style in hairstyle_options
                else 0
            )
            hair_style = st.selectbox(
                "发型 / Hairstyle",
                hairstyle_options,
                index=hairstyle_index,
            )

            hair_or_fur_color = st.text_input(
                "头发 / 毛发颜色 / Hair or Fur Color",
                value=draft.hair_or_fur_color,
            )

            body_build_options = [
                "",
                "很瘦 / Very slim",
                "偏瘦 / Slim",
                "普通 / Average",
                "圆润 / Round",
                "胖胖的 / Chubby",
                "壮壮的 / Strong",
            ]
            body_build_index = (
                body_build_options.index(draft.body_build)
                if draft.body_build in body_build_options
                else 0
            )
            body_build = st.selectbox(
                "体型 / Body Build",
                body_build_options,
                index=body_build_index,
            )

            height_options = [
                "",
                "很矮 / Very short",
                "偏矮 / Short",
                "中等 / Medium",
                "偏高 / Tall",
                "很高 / Very tall",
            ]
            height_index = (
                height_options.index(draft.height)
                if draft.height in height_options
                else 0
            )
            height = st.selectbox(
                "身高感觉 / Height Category",
                height_options,
                index=height_index,
            )

            height_cm = st.number_input(
                "精确身高 / Exact Height (cm, optional)",
                min_value=1.0,
                max_value=1000.0,
                value=float(draft.height_cm or 120.0),
                step=1.0,
                help="SECTION 1.2 会用 Reference Characters 做相对身高尺。",
            )

            favorite_colors = st.text_input(
                "喜爱的颜色 / Favorite Colors",
                value="，".join(draft.favorite_colors),
                placeholder="例如：粉色，蓝色",
            )

        with c2:
            personality = st.text_input(
                "性格 / Personality",
                value="，".join(draft.personality_traits),
            )
            speaking_tone = st.text_input(
                "说话语气 / Speaking Tone",
                value=draft.speaking_tone,
                placeholder="例如：温柔、有点害羞、说话慢慢的",
            )
            native_language = st.text_input(
                "母语 / Native Language",
                value=draft.native_language,
                placeholder="例如：中文 / Chinese",
            )
            english_level = st.slider(
                "英语水平 / English Level",
                min_value=1,
                max_value=10,
                value=draft.english_level or 5,
                help="1 = 几乎不会 / Almost none · 10 = 母语水平 / Native",
            )
            eye_color = st.text_input(
                "眼睛颜色 / Eye Color",
                value=draft.eyes.color,
            )

        with st.expander("🎨 Detail / 更多细节", expanded=False):
            d1, d2 = st.columns(2)

            with d1:
                story_role = st.text_input(
                    "故事角色定位 / Story Role",
                    value=draft.story_role,
                    placeholder="例如：Traveler、Explorer、Inventor",
                )
                body_type = st.text_input(
                    "身体类型 / Body Type",
                    value=draft.body_type,
                )
                proportions = st.text_input(
                    "身体比例 / Proportions",
                    value=draft.proportions,
                )
                face = st.text_input(
                    "脸部 / Face",
                    value=draft.face,
                )
                eye_shape = st.text_input(
                    "眼睛形状 / Eye Shape",
                    value=draft.eyes.shape,
                )
                eye_size = st.text_input(
                    "眼睛大小 / Eye Size",
                    value=draft.eyes.size,
                )
                eye_special = st.text_input(
                    "眼睛特别特征 / Eye Special Features",
                    value="，".join(draft.eyes.special_features),
                )
                skin_fur_material = st.text_input(
                    "皮肤 / 毛发 / 材质 / Skin, Fur or Material",
                    value=draft.skin_fur_material,
                )

            with d2:
                distinctive = st.text_input(
                    "特别特征 / Distinctive Features",
                    value="，".join(draft.distinctive_features),
                )
                strengths = st.text_input(
                    "擅长 / Strengths",
                    value="，".join(draft.strengths),
                )
                weaknesses = st.text_input(
                    "弱点 / Weaknesses",
                    value="，".join(draft.weaknesses),
                )
                fears = st.text_input(
                    "害怕什么 / Fears",
                    value="，".join(draft.fears),
                )
                habits = st.text_input(
                    "小习惯 / Habits",
                    value="，".join(draft.habits),
                )
                likes = st.text_input(
                    "喜欢 / Likes",
                    value="，".join(draft.likes),
                )
                dislikes = st.text_input(
                    "不喜欢 / Dislikes",
                    value="，".join(draft.dislikes),
                )
                abilities = st.text_input(
                    "能力 / Abilities",
                    value="，".join(draft.abilities),
                )

        prop_assets = ctx.repository.list_assets(AssetType.PROP)
        selected_props = st.multiselect(
            "🎒 初始道具 / Starting Props（最多 2 个 / max 2）",
            prop_assets,
            default=[
                prop
                for prop in prop_assets
                if prop.asset_id in draft.starting_prop_ids
            ],
            format_func=lambda asset: asset.display_name,
            max_selections=2,
        )

        st.caption(
            "👕 上衣、裤子、鞋子、帽子和配饰已经在数据结构中作为 "
            "WEAR Asset 引用；Wearable Library 会在后续 Factory 中接入。"
        )

        if st.button(
            "❤️ Save This Character / 保存角色",
            type="primary",
            disabled=not name.strip(),
        ):
            final_profile = draft.model_copy(
                update={
                    "source_description": st.session_state.get(
                        "char_source", ""
                    ),
                    "character_type": character_type,
                    "age": age,
                    "appearance": appearance,
                    "hair_or_fur": hair_or_fur,
                    "hair_style": hair_style,
                    "hair_or_fur_color": hair_or_fur_color,
                    "body_build": body_build,
                    "height": height,
                    "height_cm": height_cm,
                    "favorite_colors": split_items(favorite_colors),
                    "personality_traits": split_items(personality),
                    "speaking_tone": speaking_tone,
                    "native_language": native_language,
                    "english_level": english_level,
                    "story_role": story_role,
                    "body_type": body_type,
                    "proportions": proportions,
                    "face": face,
                    "eyes": EyeProfile(
                        shape=eye_shape,
                        color=eye_color,
                        size=eye_size,
                        special_features=split_items(eye_special),
                    ),
                    "skin_fur_material": skin_fur_material,
                    "distinctive_features": split_items(distinctive),
                    "strengths": split_items(strengths),
                    "weaknesses": split_items(weaknesses),
                    "fears": split_items(fears),
                    "habits": split_items(habits),
                    "likes": split_items(likes),
                    "dislikes": split_items(dislikes),
                    "abilities": split_items(abilities),
                    "starting_prop_ids": [
                        prop.asset_id for prop in selected_props
                    ],
                }
            )

            missing = final_profile.missing_core_fields()

            if missing:
                st.warning(
                    "还有核心设定没有完成 / Core fields still missing: "
                    + ", ".join(missing)
                )
            else:
                asset = character_factory.save_character(
                    name=name,
                    description=st.session_state.get(
                        "char_source", ""
                    ),
                    profile=final_profile,
                )

                st.success(
                    f"保存成功：{asset.display_name} · {asset.asset_id}"
                )

                st.session_state.char_draft = None

                st.caption(
                    "下一阶段会把 Master Reference、Front / Side / Back、"
                    "表情、姿势都挂在这个 CHAR_ID 下。"
                )


elif page == "🌎 Mini Utopia":
    st.header("🌎 Mini Utopia")
    st.subheader(universe.tagline)
    st.write(universe.description)

    st.markdown(
        "**Story Formula** · "
        + " → ".join(universe.story_formula)
    )

    st.markdown(
        "**Portal Rule** · "
        + universe.portal_rule
    )

    st.markdown("**Canon Rules**")

    for rule in universe.canon_rules:
        st.write("✓ " + rule)

    if universe.traveler_asset_id:
        traveler = ctx.repository.get_asset(
            universe.traveler_asset_id
        )

        st.success(
            "Current Traveler: "
            + (
                traveler.display_name
                if traveler
                else universe.traveler_asset_id
            )
        )
    else:
        st.caption(
            "Traveler 尚未锁定。确认第一个 Character Master 后"
            "再设为 Mini Utopia Traveler。"
        )


elif page == "🧪 Playground":
    st.header("🧪 Playground")
    st.write(
        "No rules. No canon. Just create. "
        "这里的实验不会自动改变 Mini Utopia。"
    )

    title = st.text_input("给这个疯狂想法一个名字")

    premise = st.text_area(
        "发生什么？",
        placeholder="例如：写实恐龙和水彩香蕉在学校打篮球……",
    )

    chars = ctx.repository.list_assets(AssetType.CHARACTER)

    selected = st.multiselect(
        "想带上哪些已有角色？",
        chars,
        format_func=lambda asset: asset.display_name,
    )

    if st.button(
        "Save Playground Story",
        disabled=not title or not premise,
    ):
        story = ctx.stories.create_story(
            title=title,
            premise=premise,
            mode=StoryMode.PLAYGROUND,
            asset_ids=[
                asset.asset_id
                for asset in selected
            ],
        )

        st.success(
            f"已保存：{story.story_id}"
        )


elif page == "📖 Stories":
    st.header("📖 Stories")

    stories = ctx.repository.list_stories()

    if not stories:
        st.info(
            "还没有 Story。可以先在 Playground 保存一个疯狂想法。"
        )

    for story in stories:
        with st.container(border=True):
            st.subheader(story.title)
            st.caption(
                f"{story.story_id} · {story.mode.value}"
            )
            st.write(story.premise)
            st.caption(
                "Assets: "
                + (
                    ", ".join(story.asset_ids)
                    or "none"
                )
            )


# ---------------------------------------------------------------------------
# Studio-only inspector
# This block is unreachable unless Studio authentication succeeded above.
# ---------------------------------------------------------------------------

if mode == "🛠 Studio" and studio_unlocked:
    st.divider()
    st.subheader("🛠 Studio Inspector")

    with st.expander(
        "Universe",
        expanded=False,
    ):
        st.json(
            universe.model_dump(mode="json")
        )

    with st.expander(
        "Assets",
        expanded=False,
    ):
        st.json(
            [
                asset.model_dump(mode="json")
                for asset in ctx.repository.list_assets()
            ]
        )

    with st.expander(
        "Jobs",
        expanded=False,
    ):
        st.json(
            [
                job.model_dump(mode="json")
                for job in ctx.repository.list_jobs()
            ]
        )
