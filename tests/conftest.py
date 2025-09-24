import pytest

variant_data = {
    "8466140": {"rsid": "rs10085558", "variant": "7:37945678"},
    "8466253": {"rsid": "rs79590116", "variant": "7:37964907"},
}

@pytest.fixture(scope="session")
def variants_in_studies_db():
    return variant_data


@pytest.fixture(scope="session")
def variants_in_ld_db():
    return {
        "8466140": "7:37945678",
        "8466253": "7:37964907",
    }

@pytest.fixture(scope="session")
def variants_in_grange():
    return "7:37945678-37964907"