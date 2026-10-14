import hashlib

from studio.bridge.family_api import FamilyAPIApplication, FamilyPrincipal


def test_denies_unassigned_character():
    adult = FamilyPrincipal('adult', 'adult', hashlib.sha256(b'example-adult').hexdigest())
    child = FamilyPrincipal('child', 'child', hashlib.sha256(b'example-child').hexdigest(), frozenset({'CHAR_A'}))
    app = FamilyAPIApplication(principals=[adult, child], allowed_origins=['https://example.test'])
    response = app.handle(method='GET', path='/characters/CHAR_B')
    assert response.status == 401
