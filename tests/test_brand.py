from studio.ui.brand import BRAND_NAME, BRAND_TAGLINE, HORIZONTAL_LOGO_SVG, SQUARE_LOGO_SVG


def test_brand_canon_has_primary_identity():
    assert BRAND_NAME == "Mini Utopia"
    assert BRAND_TAGLINE == "Travel Around Every World"


def test_brand_canon_exposes_both_logo_formats():
    assert "mu-sidebar-logo" in SQUARE_LOGO_SVG
    assert "mu-primary-logo" in HORIZONTAL_LOGO_SVG
    assert "Mini Utopia" in HORIZONTAL_LOGO_SVG
