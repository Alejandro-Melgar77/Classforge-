import pytest

@pytest.fixture(autouse=True)
def setup_db():
    """Override root setup_db fixture so codegen tests run without MongoDB."""
    yield
