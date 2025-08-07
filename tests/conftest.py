import pytest


@pytest.fixture(scope="session")
def variants_in_studies_db():
    return {
        "8466253": {"rsid": "rs79590116", "variant": "7:37964907_A_G"},
        "8466097": {"rsid": "rs2598104", "variant": "7:37937647_C_T"},
    }


@pytest.fixture(scope="session")
def variants_in_ld_db():
    return {
        "8466253": "7:37964907_A_G",
        "8466097": "7:37937647_C_T",
    }
