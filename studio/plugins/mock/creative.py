from studio.models.character import CharacterProfile
from studio.plugins.base import Plugin


class MockCharacterParsePlugin(Plugin):
    capability = "character.parse"
    provider = "mock"

    def execute(self, **kwargs) -> CharacterProfile:
        description = kwargs.get("description", "")
        lower = description.lower()
        species = "大熊猫" if "熊猫" in description or "panda" in lower else "原创角色"
        clothing = "黄色帽子、蓝色背带裤" if ("黄色" in description and "蓝色" in description) else ""
        personality = []
        for word in ["胆小", "勇敢", "好奇", "调皮", "安静", "搞笑"]:
            if word in description:
                personality.append(word)
        return CharacterProfile(
            species=species,
            body="胖胖的" if "胖" in description else "",
            face="圆润、友善",
            clothing=clothing,
            personality=personality or ["好奇"],
            strengths=["愿意探索"],
            weaknesses=["容易紧张"] if "胆小" in description else [],
            immutable_features=[x for x in [species, clothing] if x],
        )


class MockTurnaroundPlugin(Plugin):
    capability = "character.turnaround"
    provider = "mock"

    def execute(self, **kwargs):
        return {
            "status": "placeholder",
            "message": "Turnaround provider is ready to be connected; no image is generated in Foundation v0.3.",
        }
