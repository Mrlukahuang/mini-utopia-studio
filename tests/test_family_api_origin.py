import hashlib

from studio.bridge.family_api import FamilyAPIApplication, FamilyPrincipal


def test_https_origin_validation():
    adult = FamilyPrincipal('adult', 'adult', hashlib.sha256(b'example').hexdigest())
    try:
        FamilyAPIApplication(principals=[adult], allowed_origins=['http://example.test'])
    except ValueError:
        return
    raise AssertionError('HTTP must be rejected')
