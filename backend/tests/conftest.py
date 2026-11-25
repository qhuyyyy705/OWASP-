import os
import tempfile
import pytest

_test_db_dir = tempfile.TemporaryDirectory(prefix="websentinel-tests-")
os.environ["WEBSENTINEL_DB_PATH"] = os.path.join(_test_db_dir.name, "test.sqlite3")
os.environ["WEBSENTINEL_DATA_DIR"] = _test_db_dir.name

@pytest.fixture(autouse=True)
def clean_database():
    from app.database.session import Base, engine
    from app import models  # noqa: F401
    from app.services.proxy_manager import proxy_manager
    proxy_manager.stop()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def pytest_sessionfinish(session, exitstatus):
    from app.database.session import engine
    engine.dispose()
    _test_db_dir.cleanup()
