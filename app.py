from pathlib import Path
import streamlit as st
from studio.core.config import get_settings
from studio.core.enums import AssetType, StoryMode
from studio.models.character import CharacterProfile
from studio.recipes.character_factory import CharacterFactoryRecipe
from studio.services.bootstrap import build_context

ROOT = Path(__file__).parent
ctx = build_context(get_settings(ROOT))
universe = ctx.universes.ensure_mini_utopia()
character_factory = CharacterFactoryRecipe(ctx.registry, ctx.assets)

st.set_page_config(page_title="Mini Utopia Studio", page_icon="✨", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1180px;padding-top:2rem}
.stButton>button{border-radius:16px}
[data-testid='stMetric']{background:#F7F3FF;padding:14px;border-radius:18px}
.mu-card{padding:18px;border:1px solid #ebe6ff;border-radius:20px;background:#fff}
</style>
""", unsafe_allow_html=True)

st.title("✨ Mini Utopia · AI Creative Studio")
mode = st.sidebar.radio("Mode", ["🧒 Creator", "🛠 Studio"])
page = st.sidebar.radio("Create", ["🏠 Home", "🎭 My Characters", "✨ Character Factory", "🌎 Mini Utopia", "🧪 Playground", "📖 Stories"])

if "char_draft" not in st.session_state:
    st.session_state.char_draft = None

if page == "🏠 Home":
    st.subheader("Small Worlds. Big Imagination.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎭 Characters", len(ctx.repository.list_assets(AssetType.CHARACTER)))
    c2.metric("🌍 Places", len(ctx.repository.list_assets(AssetType.LOCATION)))
    c3.metric("🎒 Objects", len(ctx.repository.list_assets(AssetType.PROP)))
    c4.metric("📖 Stories", len(ctx.repository.list_stories()))
    st.info("角色、地点、道具和风格都是独立资产。Story 只负责把它们自由组合。")

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
            st.write(" · ".join(profile.get("personality", [])) or "等待性格设定")

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
            split = lambda s: [x.strip() for x in s.replace("，", ",").split(",") if x.strip()]
            final_profile = draft.model_copy(update={
                "species": species,
                "body": body,
                "face": face,
                "clothing": clothing,
                "personality": split(personality),
                "strengths": split(strengths),
                "weaknesses": split(weaknesses),
                "immutable_features": split(immutable),
            })
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
    selected = st.multiselect("想带上哪些已有角色？", chars, format_func=lambda a: a.display_name)
    if st.button("Save Playground Story", disabled=not title or not premise):
        story = ctx.stories.create_story(
            title=title,
            premise=premise,
            mode=StoryMode.PLAYGROUND,
            asset_ids=[a.asset_id for a in selected],
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
    st.sidebar.caption("Foundation v0.3")
    st.sidebar.caption("Capabilities: " + ", ".join(ctx.registry.list_capabilities()))
    with st.expander("🛠 Studio Inspector"):
        st.write("Universe")
        st.json(universe.model_dump(mode="json"))
        st.write("Assets")
        st.json([a.model_dump(mode="json") for a in ctx.repository.list_assets()])
        st.write("Jobs")
        st.json([j.model_dump(mode="json") for j in ctx.repository.list_jobs()])
