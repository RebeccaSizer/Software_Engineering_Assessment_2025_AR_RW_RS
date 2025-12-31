import time
import json
import sqlite3
import requests
from tools.utils.logger import logger
from http.client import RemoteDisconnected


def request_status_codes(e, variant, url, API, attempt):
    """
    This function handles requests.exceptions.HTTPError exceptions that arise from requests.get responses that have one
    of the following status codes: 400, 404, 408, 429, 500, 503 or 504. These are some of the most common status codes
    to receive when an HTTPError exception is raised.
    This function uses the exception (e), the variant, the API being queried, the request URL and attempt (if multiple
    attempts are being made to receive a response) to configure log messages and flash messages tailored around the
    response error being handled.
    Flash messages appear to Users of the flask app while the log messages are either printed to the stdout or log file,
    depending on their log level.
    As requests.get is used to query APIs, this error handler function is implemented in vv_functions.py and
    clinvar_functions.py.

    :params: e: An abbreviation of the Exception that was raised. As this function is only used in response to
                requests.exceptions.HTTPError, e will always be requests.exceptions.HTTPError. e is imported from the
                exception so that the error message can be used in the log and flash messages.
          E.g.: requests.exceptions.HTTPError: 404 Client Error: Not Found for url:
                https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T
                /mane?content-type=application%2Fjson'

       variant: The variant being queried in the request to the API. This may not always be a variant but in most cases
                it is. The value represented by 'variant' is used to denote what is being queried and provide context so
                that the User can understand where or why the exception was raised.
          E.g.: '11-2164285-C-T'
                'ClinVar_Download'

           url: The URL used in the request that raised the HTTPError exception.
          E.g.: 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T
                 /mane?content-type=application%2Fjson'

           API: The API being queried in the request that raised the HTTPError exception.
          E.g.: 'VariantValidator'
                'ClinVar'

       Attempt: The number of the attempt when the HTTPError exception was raised. Requests are retried when a
                response has either a 408 or 429 status code, by iterating through up to 5 attempts.
          E.g.: '0', '1', '2', '3', '4'

    :output: A message that will be incorporated into a flash message that will be displayed to the User on the
             flask app.
       E.g.: '11-2164285-C-T: ❌ HTTPError 400: Bad Request. VariantValidator API did not accept this variant
             description.'

    :command: url = 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T'
                    '/mane?content-type=application%2Fjson'

              for attempt in range(5):
                  try:
                    response = requests.get(url)
                  except requests.exceptions.HTTPError as e:
                    error_message = request_status_codes(e, '11-2164285-C-T', url, 'VariantValidator', attemnpt)
                    flash(error_message)
    """
    # Handle a 400 Bad Requests status error code. Log the error and return a message to notify the User.
    if e.response.status_code == 400:
        logger.error(f'{variant}: HTTPError 400: Bad Request. {API} API could not process this request: {url}')
        return f'{variant}: ❌ HTTPError 400: Bad Request. {API} API did not accept this variant description.'

    # Handle a 404 Not Found status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 404:
        logger.error(
            f'{variant}: HTTPError 404: Not Found. {API} API could not locate an endpoint from this request: {url}')
        return (f'{variant}: ❌ HTTPError 404: Not Found. '
                f'{API} API could not find a response to this variant description.')

    # Handle a 408 Request Timeout status error code
    elif e.response.status_code == 408:

        if attempt < 3:
            # Create a delay between attempts if 408 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(
                f'{variant}: HTTPError 408: Request Timeout. Request could not reach {API} server in time: {url}')
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/3')

        else:
            logger.error(f'{variant}: HTTPError 408 status: Request Timeout. '
                         f'The remote server dropped the connection before {API} could receive the request: {url}')
            return f'{variant}: ❌ HTTPError 408: {API} dropped the connection. Please try again later.'

    # Handle a 429 Too Many Requests status error code
    elif e.response.status_code == 429:

        if attempt < 4:
            # Create a delay between attempts if 429 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(
                f'{variant}: HTTPError 429: Too Many Requests. {API} is currently overloaded with requests.{url}')
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/5')

        else:
            logger.error(
                f'{variant}: HTTPError 429 persisted: Too Many Requests. {API} was overloaded with requests.{url}')
            return f'{variant}: ❌ HTTPError 429: {API} is currently overloaded with requests. Please try again later.'

    # Handle a 500 Internal Server Error status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 500:
        logger.error(f'{variant}: HTTPError 500: Internal Server Error. {API} API server crashed. {url}')
        return (f'{variant}: ❌ HTTPError 500: '
                f'Internal Server Error. {API} API server crashed. Its not your fault. Please try again later.')

    # Handle a 503 Service Unavailable status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 503:
        logger.error(f'{variant}: HTTPError 503: '
                     f'Service Temporarily Unavailable. {API} API is overloaded or down for maintenance. {url}')
        return (f'{variant}: ❌ HTTPError 503: '
                f'Service Unavailable. {API} API is unavailable. Its not your fault. Please try again later.')

    # Handle a 504 Gateway Timeout status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 504:
        logger.error(f'{variant}: HTTPError 504: Gateway Timeout. {API} API took too long to respond.')
        return (f'{variant}: ❌ HTTPError 504: '
                f'Gateway Timeout. {API} API response took too long. Its not your fault. Please try again later.')

    # Handle other HTTPErrors. Log the error and return a message to notify the User.
    else:
        logger.error(f'{variant}: HTTPError: {API} API could not respond to this request: {url}. {e}')
        return f'{variant}: ❌ HTTPError: {API} API unavailable.'



def connection_error(e, variant, API, url):
    """
    This function handles requests.exceptions.ConnectionError exceptions that arise from using requests.get to query an
    API. The connection errors that arise include NewConnectionError and RemoteDisconnected. This function also
    generically handles all exceptions that come under the ConnectionError class.
    This function uses the exception (e), the variant, the API being queried and request URL to configure log messages
    and flash messages tailored around the response error being handled.
    Flash messages appear to Users of the flask app while the log messages are either printed to the stdout or log file,
    depending on their log level.
    As requests.get is used to query APIs, this error handler function is implemented in vv_functions.py and
    clinvar_functions.py.

    :params: e: An abbreviation of the Exception that was raised. As this function is only used in response to
                requests.exceptions.ConnectionError, e will always be requests.exceptions.ConnectionError. e is imported
                from the exception so that the error message can be used in the log and flash messages.
          E.g.: requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=5000): Max retries
                exceeded with url: /api/data (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at
                0x7f8c2a1b2f10>: Failed to establish a new connection: [Errno 111] Connection refused'))

                https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T
                /mane?content-type=application%2Fjson'

       variant: The variant being queried in the request to the API. This may not always be a variant but in most cases
                it is. The value represented by 'variant' is used to denote what is being queried and provide context so
                that the User can understand where or why the exception was raised.
          E.g.: '11-2164285-C-T'
                'ClinVar_Download'

           url: The URL used in the request that raised the ConnectionError exception.
          E.g.: 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T
                 /mane?content-type=application%2Fjson'

           API: The API being queried in the request that raised the ConnectionError exception.
          E.g.: 'VariantValidator'
                'ClinVar'

    :output: A message that will be incorporated into a flash message that will be displayed to the User on the
             flask app.
       E.g.: '11-2164285-C-T: ❌ VariantValidator server dropped the connection before sending a response.'

    :command: url = 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T'
                    '/mane?content-type=application%2Fjson'
              try:
                response = requests.get(url)
              except requests.exceptions.ConnectionError as e:
                error_message = connection_error(e, '11-2164285-C-T', url, 'VariantValidator')
                flash(error_message)
    """

    # Retrieve the cause of the ConnectionError exception.
    cause = e.__cause__
    # Grab the error number if it exists by checking if the cause exists.
    errno = getattr(cause, "errno", None)
    # Search if the cause comes under the OSError class of exceptions and was due to a poor internet connection
    # (denoted as 101).
    if isinstance(cause, OSError) and errno == 101:
        # Log the ConnectionError.
        logger.error(f'{variant}: NewConnectionError [101]: There was an error connecting to the internet. Request: {url}. {e}')
        # Return a flash message to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User understand where along the API request process failed.
        return f'{variant}: ❌ NewConnectionError [101]: There was a problem with your internet connection. Please check your WiFi, VPN or ethernet connection.'

    # Log RemoteDisconnected exceptions.
    if isinstance(cause, RemoteDisconnected):
        logger.error(f'{variant}: RemoteDisconnected: {API} server dropped the connection. Request: {url}. {e}')
        # Return a flash message to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User understand where along the API request process failed.
        return f'{variant}: ❌ {API} server dropped the connection before sending a response.'

    # Log any other ConnectionError.
    else:
        if errno:
            # Log an error number is provided in 'cause', provide it in the logger message.
            logger.error(f'{variant}: ConnectionError [{errno}]: There was an error connecting with the remote server. Request: {url}. {e}')
        else:
            # If an error number is not provided in 'cause', leave a generic logger message.
            logger.error(f'{variant}: ConnectionError: There was an error connecting with the remote server. Request: {url}. {e}')
        # Return a flash message to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User understand where along the API request process failed.
        return f'{variant}: ❌ There was a problem with your connection with the remote server.'



def json_decoder_error(e, variant, url):
    """
    This function handles json.decoder.JSONDecodeError exceptions that arise from the responses received when querying
    an API using requests.get. Such errors typically occur when a response is meant to be in JSON format but something
    about it prevents it fulfilling a complete JSON structure. This can include a missing closing bracket  at the end
    of the JSON or trying to use the json.loads() function on an empty JSON.
    This function uses the exception (e), the variant and the request URL to configure log messages and flash messages
    tailored around the response error being handled.
    Flash messages appear to Users of the flask app while the log messages are either printed to the stdout or log file,
    depending on their log level.
    As VariantValidator is the only API queried by this software package that returns responses in JSON, this error
    handler function is implemented in vv_functions.py.

    :params: e: An abbreviation of the Exception that was raised. As this function is only used in response to
                json.decoder.JSONDecodeError, e will always be json.decoder.JSONDecodeError. e is imported
                from the exception so that the error message can be included in the log message.
          E.g.: json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column
                28 (char 27)

       variant: The variant being queried in the request to the API. This will always be a variant. The variant is used
                to denote what is being queried and provide context so that the User can understand where or why the
                exception was raised.
          E.g.: '11-2164285-C-T'

           url: The URL used in the request that raised the ConnectionError exception.
          E.g.: 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T
                 /mane?content-type=application%2Fjson'

    :output: A message that will be incorporated into a flash message that will be displayed to the User on the
             flask app.
       E.g.: '11-2164285-C-T: ❌ Response from VariantValidator was not in JSON format.'

    :command: url = 'https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/11-2164285-C-T'
                    '/mane?content-type=application%2Fjson'
              try:
                response = requests.get(url)
              except json.decoder.JSONDecodeError as e:
                error_message = json_decoder_error(e, '11-2164285-C-T', url)
                flash(error_message)
    """
    # Log JSONDecodeError exceptions.
    logger.error(
        f'{variant}: JSONDecodeError from VariantValidator: Response was not in JSON format. Request: {url}. {e}')
    # Return a flash message to the function in database_functions.py, so that it can be appended to the file name.
    # This will help the User understand where along the API request process failed.
    return f'{variant}: ❌ Response from VariantValidator was not in JSON format.'



def regex_error(e, variant):
    """
    This function handles re.error exceptions that arise when there is something wrong with the Regex pattern that is
    being used to check certain values. Some of the Regex patterns are quite convoluted. In the hypothetical scenario
    where they are incorrectly changed and no longer work, an re.error exception will occur. re.errors can include
    inappropriate structures in the Regex pattern such as [z-a] instead of [a-z] or missing brackets.
    This function uses the exception (e), the variant being queried to configure log messages and flash messages
    tailored around the re.error being handled.
    Flash messages appear to Users of the flask app while the log messages are either printed to the stdout or log file,
    depending on their log level.
    As VariantValidator is the only API queried by this software package that returns responses in JSON, this error
    handler function is implemented in vv_functions.py.

    :params: e: An abbreviation of the Exception that was raised. As this function is only used in response to re.error,
                e will always be re.error. e is imported from the exception so that the error message can be included in
                the log message.
          E.g.: re.error: missing ), unterminated subpattern at position 0

       variant: The variant being queried in the request to the API. This will always be a variant. The variant is used
                to denote what is being queried and provide context so that the User can understand where or why the
                exception was raised.
          E.g.: '11-2164285-C-T'

    :output: A message that will be incorporated into a flash message that will be displayed to the User on the flask
             app.
       E.g.: '11-2164285-C-T: ❌ Internal Error: Regex validation failed. Please report this to your friendly
              neighbourhood Clinical Bioinformatician.'

    :command: gene_change = 'c.2164285C>T'
              try:
                re.match(r'^c.\\d{7[ACGT]>[ACGT]$', gene_change)
              except re.error as e:
                error_message = regex_error(e, '11-2164285-C-T')
                flash(error_message)
    """
    # Log the error if it occurs, using the exception output message.
    logger.error(f'{variant}: The Regex pattern was invalid: {e.pattern}')
    # Log a debug message describing why and where the Regex pattern broke.
    logger.debug(f'Reason: {e.msg}; Regex pattern broke at position: {e.pos}.')
    # Return the description so that the functions in database_functions.py can attach the description
    # to the file name where the queried variant comes from. This will help the User.
    return (f'{variant}: ❌ Internal Error: Regex validation failed. Please report this to your friendly neighbourhood '
            f'Clinical Bioinformatician.')


# Error handler executed in exceptions related to sqlite3.
def sqlite_error(e, db_name):
    """
    This function handles sqlite3.OperationalError, sqlite3.DatabaseError and sqlite3.ProgrammingError exceptions that
    arise when the imported sqlite3 module is used to interact with SQLite3 databases on Python.
    This function uses the exception (e) and the name of the database being connected to, to configure log messages
    around the type of SQLite3 error being handled.
    A generic flash messages is returned to Users of the flask app because the expected User will not understand much
    about SQLite3 errors and will not know how to resolve them. Log messages are either printed to the stdout or log
    file, depending on their log level.
    As SQLite3 is only implemented in the creation of clinvar.db and any user-defined databases, this error handler
    function is implemented in clinvar_functions.py and database_functions.py.

    :params: e: An abbreviation of the SQLite3 exception that was raised. The specific SQLite3 exceptions that this
                function handles are: sqlite3.OperationalError, sqlite3.DatabaseError and sqlite3.ProgrammingError. e
                is imported from the exception so that the error message can be used in log messages.
          E.g.: sqlite3.OperationalError: no such table: patient_varian

       db_name: The name of the database being processed by SQLite3.
          E.g.: 'my_database.db'

    :output: A generic message that can be incorporated into a flash message, that will be displayed to the User on the
             flask app.
       E.g.: 'There is something wrong with the database. Please report this to your friendly neighbourhood Clinical
              Bioinformatician.'

    :command: db_name = 'my_database.db'
              try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_varian (
                                                              No INTEGER PRIMARY KEY,
                                                              patient_ID TEXT NOT NULL,
                                                              variant TEXT NOT NULL,
                                                              UNIQUE(patient_ID, variant)
                   )
                ''')

              except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
                error_message = sqlite_error(e, f'{db_name}.db')
                flash(f'❌ patient_variant_table SQLite3 Error: {error_message}.')
    """
    if isinstance(e, sqlite3.OperationalError):
        # Log the error if an OperationalError occurs, using the exception output message.
        logger.error(f'sqlite3.OperationalError: {db_name} is not working properly: {e}')

    # Log the error if a DatabaseError occurs, using the exception output message.
    if isinstance(e, sqlite3.DatabaseError):
        # Log the error if an DatabaseError occurs, using the exception output message.
        logger.error(f'sqlite3.DatabaseError: There is a problem with {db_name}: {e}')

    # Log the error if a ProgrammingError occurs, using the exception output message.
    if isinstance(e, sqlite3.ProgrammingError):
        # Log the error if an DatabaseError occurs, using the exception output message.
        logger.error(f'sqlite3.ProgrammingError: There is a programmatic issue with {db_name}: {e}')

    # Return a message to be used in a flash message.
    return (f'Something went wrong while accessing the database. '
            f'Please report this to your friendly neighbourhood Clinical Bioinformatician.')









"""
for attempt in range(7):

    try:
        url = "http://example.com"
        response = requests.get(url)
        # response.raise_for_status()

        data = response.json()

    except ValueError as e:

        error_message = json_decoder_error(e, 'test', 'test_api', url)
        print(error_message)




    # Catch any network or HTTP errors raised by 'requests'.
    except requests.exceptions.HTTPError as e:

        # Handle HTTP errors that need to be tried again.
        if e.response.status_code in [408, 429]:
            error_message = request_status_codes(e, 'test', url, 'test_API', attempt)

            # Once received, return any flash messages to the function in database_functions.py, so that it can
            # be appended to the file name. This will help the User where along the API request process failed.
            if error_message:
                print(error_message)

            continue

        # Handle HTTP errors that do not need to be tried again.
        else:
            error_message = request_status_codes(e, 'test', url, 'test_API', attempt)

        # Return any flash messages to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User where along the API request process failed.
        print(error_message)

"""