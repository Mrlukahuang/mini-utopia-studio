from studio.models.character import CharacterProfile, EyeProfile
from studio.plugins.base import Plugin


class MockCharacterParsePlugin(Plugin):
    capability = "character.parse"
    provider = "mock"

    def execute(self, **kwargs) -> CharacterProfile:
        description = kwargs.get("description", "")
        lower = description.lower()

        character_type = (
            "大熊猫"
            if "熊猫" in description or "panda" in lower
            else "原创角色"
        )

        personality = []
        for word in ["胆小", "勇敢", "好奇", "调皮", "安静", "搞笑"]:
            if word in description:
                personality.append(word)

        favorite_colors = []
        if "黄色" in description or "yellow" in lower:
            favorite_colors.append("黄色")
        if "蓝色" in description or "blue" in lower:
            favorite_colors.append("蓝色")

        immutable = [character_type]
        if "胖" in description:
            immutable.append("胖胖的体型")

        return CharacterProfile(
            source_description=description,
            character_type=character_type,
            appearance="胖胖的" if "胖" in description else "",
            body_type="胖胖的" if "胖" in description else "",
            face="圆润、友善",
            eyes=EyeProfile(shape="圆润"),
            favorite_colors=favorite_colors,
            personality_traits=personality or ["好奇"],
            strengths=["愿意探索"],
            weaknesses=["容易紧张"] if "胆小" in description else [],
            immutable_features=immutable,
        )


class MockTurnaroundPlugin(Plugin):
    capability = "character.turnaround"
    provider = "mock"

    def execute(self, **kwargs):
        return {
            "status": "placeholder",
            "message": (
                "Turnaround provider is ready to be connected; "
                "no image is generated in Foundation v0.3."
            ),
        }
