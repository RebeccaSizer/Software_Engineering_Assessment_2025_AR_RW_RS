"""
Unit tests for main (main.py).

This module contains pytest-based tests that verify correct behaviour
and error handling for functions in main. Some external
dependencies such as databases, files, and network requests are mocked
using pytest fixtures (e.g. monkeypatch) to ensure deterministic and
isolated testing.

Some tests were initially generated with assistance from ChatGPT and
subsequently refined by the developer.
"""

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
    This function tests if main.py can successfully detect clinvar.db, if it exists.
    monkeypatch pytest fixture is used to simulate the existence of the clinvar.db file.
    mock_logger is used to test that the expected logger message, "ClinVar database available. No download needed." is
    returned. This message is logged if clinvar.db has been detected.
    """
    from main import clinvar_db_check

    # Monkeypatch simulates a check that confirms the existence of the clinvar.db database, in main.py.
    monkeypatch.setattr("main.os.path.exists", lambda _: True)
    # Monkeypatch simulates clinvar_vs_download from main.py but does not return anything as a result.
    monkeypatch.setattr("main.clinvar_vs_download", lambda: None)
    # The clinvar.db check function from main.py is executed using a fake filepath.
    clinvar_db_check("fake/path/clinvar.db")
    # If clinvar.db exists, clinvar_db_check() logs the message, "ClinVar database available. No download needed."
    mock_logger.info.assert_any_call(
        "ClinVar database available. No download needed."
    )

def test_clinvar_db_missing_triggers_download(monkeypatch, mock_logger):
    """
    This function tests if main.py can successfully download and create a version of clinvar.db, if it does not already
    exist.
    monkeypatch pytest fixture is used to simulate the absence of the clinvar.db file and initialise the
    clinvar_vs_download function from clinvar_functions.py, as a result.
    mock_logger is used to test that the expected logger message, "ClinVar database successfully downloaded." is
    returned. This message is logged if the clinvar_vs_download() function was successful.
    """
    from main import clinvar_db_check
    # A change to download_called["called"] from False to True indicates that clinvar_vs_download() has been executed
    # because clinvar.db is missing.
    download_called = {"called": False}

    def fake_download():
        """
        This function changes download_called["called"] to True.
        It is triggered when clinvar_vs_download() function is called.
        """
        # Change download_called["called"] from False to True.
        download_called["called"] = True
    # Monkeypatch uses the os.path.exists() function from main.py to simulate the absence of clinvar.db.
    monkeypatch.setattr("main.os.path.exists", lambda _: False)
    # Monkeypatch simulates the activation of clinvar_vs_download() function from main.py but triggers the fake_download
    # function as a result.
    monkeypatch.setattr(
        "main.clinvar_vs_download",
        fake_download
    )
    # The clinvar.db check function from main.py is executed using a fake filepath.
    clinvar_db_check("fake/path/clinvar.db")
    # If clinvar_vs_download was called, download_called["called"] should have been changed from False to True.
    assert download_called["called"] is True
    # Also clinvar_db_check() should have logged the message, "ClinVar database successfully downloaded."
    mock_logger.info.assert_any_call(
        "ClinVar database successfully downloaded."
    )

def test_open_browser_success(monkeypatch):
    """
    This function tests if the open_browser() function from main.py can successfully open the url,
    "http://127.0.0.1:5000", in a web browser.
    monkeypatch pytest fixture simulates the activation of open_browser() by trigger a fake function called
    "fake_open()", which adds the url to the 'opened' Python dictionary.
    """
    from main import open_browser
    # Adding the url to the 'openeed' Python dictionary indicates that open_browser() has been called.
    opened = {}

    def fake_open(url):
        """
        This function adds the url to the 'open' Python dictionary.
        It is triggered when the open_browser() function is called.
        """
        # Add the url to the "url" key, in the 'open' Python dictionary
        opened["url"] = url

    # Monkeypatch simulates the activation of the webbrowser function in open_browser(), from main.py, but triggers the
    # fake_open function as a result.
    monkeypatch.setattr("main.webbrowser.open", fake_open)
    # The open_browser() function is called to test if it functions correctly.
    open_browser()
    # If open_browser() was successful, the 'opened' Python dictionary should have been been populated by:
    # {"url": "http://127.0.0.1:5000"}.
    assert opened["url"] == "http://127.0.0.1:5000"


def test_open_browser_failure(monkeypatch, mock_logger):
    """
    This function tests if the open_browser() function from main.py can successfully handle a failure to open the url,
    "http://127.0.0.1:5000", in a web browser.

    monkeypatch pytest fixture simulates the activation of open_browser() but instead triggers a fake function called
    "raise_error", which raises a RuntimeError exception with the message, "Browser error".

    mock_logger is used to test that the logger function returns the expected warning message, "Could not launch flask
    app @ http://127.0.0.1:5000 in web browser. Browser error", indicating that the RuntimeError exception was handled
    appropriately.
    """
    from main import open_browser

    def raise_error(_):
        """
        This function raises a RuntimeError exception with the message, "Browser error".
        """
        # Raise the RuntimeError exception
        raise RuntimeError("Browser error")

    # Monkeypatch triggers the fake_open function when the webbrowser function in open_browser(), from main.py, is
    # activated.
    monkeypatch.setattr("main.webbrowser.open", raise_error)
    # The open_browser() function is called to test if it functions correctly.
    open_browser()
    # If the RuntimeError exception was handled appropriately, open_browser() logs the message, "Could not launch flask
    # app @ http://127.0.0.1:5000 in web browser. Browser error"
    mock_logger.warning.assert_called_with("Could not launch flask app @ http://127.0.0.1:5000 in web browser. "
                                           "Browser error")

def test_main_startup_success(monkeypatch, mock_logger):
    """
    This function tests if the run_app() function from main.py can successfully start the flask app in a web browser.

    Monkeypatch pytest fixture simulates the activation of the Timer() function which usually opens the URL in the web
    browser but instead triggers a fake function called "FakeTimer", which changes the value in the 'timer_started'
    Python dictionary from False to True, indicating that the Timer() function was called successfully.

    Monkeypatch pytest fixture also simulates the activation of the app.run() function which usually initialises the
    flask app in the URL defined in the open_browser() function but instead triggers a fake function called "fake_run",
    which changes the value in the 'run_called' Python dictionary from False to True, indicating that app.run() was
    called successfully.

    mock_logger is used to test that the expected logger message, "Launching flask app @ http://localhost:5000" is
    returned. This message is logged if the run_app() function was successful.
    """

    import main

    # Monkeypatch simulates the clinvar_db_check() function, from main.py, but returns a NoneType value.
    monkeypatch.setattr(main, "clinvar_db_check", lambda _: None)
    # A change to timer_started["called"] from False to True indicates that the Timer() function has been called
    # successfully.
    timer_started = {"called": False}

    class FakeTimer:
        """
        This class ultimately changes timer_started["called"] to True.
        It is triggered when the simulated Timer() function is called.
        """
        def __init__(self, *args):
            """
            This function initialises the class.
            """
            pass
        def start(self):
            """
            This function changes the value in the 'timer_started' Python dictionary to True.
            """
            timer_started["called"] = True

    # Monkeypatch triggers the FakeTimer class when the Timer() function from main.py, is activated.
    monkeypatch.setattr(main, "Timer", FakeTimer)
    # A change to run_called["called"] from False to True indicates that the app.run() function has been called
    # successfully.
    run_called = {"called": False}

    def fake_run(*args, **kwargs):
        """
        This function changes the value in the 'run_called' Python dictionary to True.
        It also uses an assertion to intercept the app.run(), and confirm that it was called correctly.
        """
        # Change the value in the 'run_called' Python dictionary to True.
        run_called["called"] = True
        # Verify that app.run() was called correctly.
        assert kwargs["debug"] is True

    # Monkeypatch triggers the fake_run function when the app.run() function from main.py, is activated.
    monkeypatch.setattr(main.app, "run", fake_run)
    # Call run_app() function from main to activate the above monkeypatches.
    main.run_app()
    # If Timer() was successful, the value in the 'timer_started' Python dictionary should change from False to True.
    assert timer_started["called"] is True
    # If app.run() was successful, the value in the 'run_called' Python dictionary should change from False to True.
    assert run_called["called"] is True
    # Also run_app() should have logged the message, "Launching flask app @ http://127.0.0.1:5000".
    mock_logger.info.assert_called_with(
        "Launching flask app @ http://localhost:5000"
    )

def test_main_clinvar_failure_exits(monkeypatch):
    """
    This function tests if the run_app() function from main.py can successfully handle errors when starting the flask
    app in a web browser.

    Monkeypatch pytest fixture simulates the activation of the clinvar_db_check() function, in the run_app() function,
    in main.py. The RuntimeError exception is raised at the point of calling the clinvar_db_check() function, along with
    the error message, "ClinVar failure". Mock_logger is used to test that the logger function returns the expected
    critical message, "ClinVar database download check failed. Application cannot be started. ClinVar failure",
    indicating that the RuntimeError exception was handled appropriately.

    Monkeypatch pytest fixture also simulates the activation of the Timer() function which usually opens the URL in the
    web browser but instead triggers a fake function called "FakeTimer", which changes the value in the 'timer_started'
    Python dictionary from False to True, indicating that the Timer() function was called successfully. However, the
    value in the 'timer_started' Python dictionary should remain False because a RuntimeError exception should be raised
    beforehand.
    """
    import main

    # A change to timer_started["called"] from False to True indicates that the Timer() function has been called
    # successfully, however,
    timer_started = {"called": False}

    class FakeTimer:
        """
        This class ultimately changes timer_started["called"] to True.
        It is triggered when the simulated Timer() function is called.
        """

        def __init__(self, *args):
            """
            This function initialises the class.
            """
            pass

        def start(self):
            """
            This function changes the value in the 'timer_started' Python dictionary to True.
            """
            timer_started["called"] = True

    # Monkeypatch triggers the FakeTimer class when the Timer() function from main.py, is activated.
    monkeypatch.setattr(main, "Timer", FakeTimer)

    def raise_error(_):
        """
        This function raises a RuntimeError exception with the message, "ClinVar failure".
        """
        # Raise the RuntimeError exception
        raise RuntimeError("ClinVar failure")

    # Monkeypatch triggers the raise_error function when the clinvar_db_check() function, from main.py, is activated.
    monkeypatch.setattr(main, "clinvar_db_check", raise_error)

    # Raise the RuntimeError exception when the run_app() function is called in main.py.
    with pytest.raises(RuntimeError):
        main.run_app()

        # The value in the 'timer_started' Python dictionary should remain False because the RuntimeError exception
        # should have been raised when the clinvar_db_check() function was called beforehand.
        assert timer_started["called"] == False

        # Also clinvar_db_check() should have logged the critical message, "ClinVar database download check failed.
        # Application cannot be started. ClinVar failure"
        mock_logger.critical.assert_any_call(
            "ClinVar database download check failed. Application cannot be started. ClinVar failure"
        )