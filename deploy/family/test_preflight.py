from deploy.family.preflight import check_preflight


def test_missing_private_host_configuration(tmp_path):
    assert check_preflight(tmp_path)
