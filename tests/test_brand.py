from studio.ui.brand import (
    BRAND_NAME,
    BRAND_TAGLINE,
    HORIZONTAL_LOGO_PATH,
    SQUARE_LOGO_PATH,
)


def test_brand_canon_has_primary_identity():
    assert BRAND_NAME == "Mini Utopia"
    assert BRAND_TAGLINE == "Travel Around Every World"


def test_brand_canon_exposes_both_logo_files():
    assert SQUARE_LOGO_PATH.exists()
    assert HORIZONTAL_LOGO_PATH.exists()
    assert SQUARE_LOGO_PATH.suffix == ".webp"
    assert HORIZONTAL_LOGO_PATH.suffix == ".webp"
