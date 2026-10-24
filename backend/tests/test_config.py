from config import Config


def test_production_config_defines_public_read_limits():
    assert Config.PUBLIC_DEFAULT_LIMIT > 0
    assert Config.PUBLIC_MAX_LIMIT >= Config.PUBLIC_DEFAULT_LIMIT
    assert Config.PUBLIC_DETAIL_LIMIT > 0
