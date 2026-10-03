from studio.models.world import WorldProfile, WorldVisualAnalysis
from studio.services.world_visual_anchor_service import WorldVisualAnchorService


class FakeVisionProvider:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = 0

    def analyze_structured(self, *, image_bytes, mime_type, prompt, schema):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return WorldVisualAnalysis(
            concept_summary="Visible floating garden",
            must_preserve=["Star Arch", "Central Lake", "Floating Main Island"],
            flexible_details=["small flowers"],
            palette_hexes=["#F7B7D2", "#B9E7D0"],
            composition_notes=["main island centered"],
            spatial_relations=["Star Arch in front of lake"],
        )


def _profile():
    return WorldProfile(
        world_name="Pastel Star Garden",
        world_type="Floating Islands / 漂浮岛",
        portal_form="Star Arch / 星星拱门",
        landmark_ideas=["Moon Castle / 月亮城堡"],
        theme_color_hexes=["#D7C2F3"],
    )


def test_visual_anchor_prefers_multimodal_image_evidence():
    provider = FakeVisionProvider()
    service = WorldVisualAnchorService(image_analysis_provider=provider)

    anchor = service.extract(
        profile=_profile(),
        concept_direction="playable",
        concept_path="assets/LOC_TEST/concept.png",
        image_bytes=b"pixels",
    )

    assert provider.calls == 1
    assert anchor.extraction_method == "openai_vision_v1"
    assert anchor.must_preserve == ["Star Arch", "Central Lake", "Floating Main Island"]
    assert anchor.composition_notes == ["main island centered"]
    assert anchor.spatial_relations == ["Star Arch in front of lake"]


def test_visual_anchor_falls_back_when_vision_provider_fails():
    service = WorldVisualAnchorService(
        image_analysis_provider=FakeVisionProvider(fail=True)
    )

    anchor = service.extract(
        profile=_profile(),
        concept_direction="playable",
        concept_path="assets/LOC_TEST/concept.png",
        image_bytes=b"pixels",
    )

    assert anchor.extraction_method == "deterministic_profile_v1"
    assert "Floating Islands / 漂浮岛" in anchor.must_preserve
    assert "Star Arch / 星星拱门" in anchor.must_preserve


def test_visual_anchor_skips_vision_without_image_bytes():
    provider = FakeVisionProvider()
    service = WorldVisualAnchorService(image_analysis_provider=provider)

    anchor = service.extract(
        profile=_profile(),
        concept_direction="playable",
        concept_path="assets/LOC_TEST/concept.png",
        image_bytes=None,
    )

    assert provider.calls == 0
    assert anchor.extraction_method == "deterministic_profile_v1"
