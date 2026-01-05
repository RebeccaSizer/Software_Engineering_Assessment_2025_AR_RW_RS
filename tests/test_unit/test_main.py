import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_logger(monkeypatch):
    """
    This function uses the monkeypatch pytest fixture and the MagicMock module to mock out the logger module from
    tools/utils, used in main.py.The logger messages are used to determine if the functions in main.py are working as
    expected.
    """
    # The output from MagicMock is assigned to the 'mock' variable.
    mock = MagicMock()
    # Monkeypatch captures the simulated logger message using 'mock', when the logger function runs in main.py.
    monkeypatch.setattr("main.logger", mock)
    # The output from MagicMock() is returned.
    return mock

def test_clinvar_db_exists(monkeypatch, mock_logger):
    """
    This function test if main.py can successfully detect clinvar.db, if it exists.
    monkeypatch pytest fixture is used to simulate the existence of the clinvar.db file.
    mock_logger is used to test that the expected logger message, "ClinVar database available. No download needed." is
    returned.
    """
    from main import clinvar_db_check


    monkeypatch.setattr("os.path.exists", lambda _: True)
    monkeypatch.setattr("tools.modules.clinvar_functions.clinvar_vs_download", lambda: None)

    clinvar_db_check("fake/path/clinvar.db")

    mock_logger.info.assert_any_call(
        "ClinVar database available. No download needed."
    )

def test_clinvar_db_missing_triggers_download(monkeypatch, mock_logger):
    from main import clinvar_db_check

    download_called = {"called": False}

    def fake_download():
        download_called["called"] = True

    monkeypatch.setattr("main.os.path.exists", lambda _: False)
    monkeypatch.setattr(
        "main.clinvar_vs_download",
        fake_download
    )

    clinvar_db_check("fake/path/clinvar.db")

    assert download_called["called"] is True
    mock_logger.info.assert_any_call(
        "ClinVar database successfully downloaded."
    )

def test_open_browser_success(monkeypatch, mock_logger):
    from main import open_browser

    opened = {}

    def fake_open(url):
        opened["url"] = url

    monkeypatch.setattr("webbrowser.open", fake_open)

    open_browser()

    assert opened["url"] == "http://127.0.0.1:5000"
    mock_logger.info.assert_called_with(
        "Launching flask app @ http://127.0.0.1:5000"
    )

def test_open_browser_failure(monkeypatch, mock_logger):
    from main import open_browser

    def raise_error(_):
        raise RuntimeError("Browser error")

    monkeypatch.setattr("webbrowser.open", raise_error)

    open_browser()

    mock_logger.warning.assert_called()

def test_main_startup_success(monkeypatch):
    import main
    import threading

    monkeypatch.setattr(main, "clinvar_db_check", lambda _: None)

    timer_started = {"called": False}

    class FakeTimer:
        def __init__(self, *args):
            pass
        def start(self):
            timer_started["called"] = True

    monkeypatch.setattr(main, "Timer", FakeTimer)

    run_called = {"called": False}

    def fake_run(*args, **kwargs):
        run_called["called"] = True
        assert kwargs["debug"] is True

    monkeypatch.setattr(main.app, "run", fake_run)

    main.run_app()

    assert timer_started["called"] is True
    assert run_called["called"] is True

def test_main_clinvar_failure_exits(monkeypatch):
    import main

    def raise_error(_):
        raise RuntimeError("ClinVar failure")

    monkeypatch.setattr(main, "clinvar_db_check", raise_error)

    with pytest.raises(RuntimeError):
        main.run_app()