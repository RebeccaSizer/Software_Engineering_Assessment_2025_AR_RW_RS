import time
import json
import requests
from tools.utils.logger import logger
from requests.exceptions import ConnectionError, HTTPError


def request_status_codes(e, variant, url, API, attempt):

    # Handle a 400 Bad Requests status error code. Log the error and return a message to notify the User.
    if e.response.status_code == 400:
        logger.error(f'{variant}: HTTPError 400: Bad Request. {API} API could not process this request: {url}')
        return f'{variant}: ❌ HTTPError 400: Bad Request. {API} API did not accept this variant description.'

    # Handle a 404 Not Found status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 404:
        logger.error(f'{variant}: HTTPError 404: Not Found. {API} API could not locate an endpoint from this request: {url}')
        return f'{variant}: ❌ HTTPError 404: Not Found. {API} API could not find a response to this variant description.'

    # Handle a 408 Request Timeout status error code
    elif e.response.status_code == 408:

        if attempt < 3:
            # Create a delay between attempts if 408 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(f'{variant}: HTTPError 408: Request Timeout. Request could not reach {API} server in time: {url}')
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/3')

        else:
            logger.error(f'{variant}: HTTPError 408 status: Request Timeout. The remote server dropped the connection before {API} could receive the request: {url}')
            return f'{variant}: ❌ HTTPError 408: {API} dropped the connection. Please try again later.'

    # Handle a 429 Too Many Requests status error code
    elif e.response.status_code == 429:

        if attempt < 4:
            # Create a delay between attempts if 429 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(f'{variant}: HTTPError 429: Too Many Requests. {API} is currently overloaded with requests.{url}')
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/5')

        else:
            logger.error(f'{variant}: HTTPError 429 persisted: Too Many Requests. {API} was overloaded with requests.{url}')
            return f'{variant}: ❌ HTTPError 429: {API} is currently overloaded with requests. Please try again later.'

    # Handle a 500 Internal Server Error status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 500:
        logger.error(f'{variant}: HTTPError 500: Internal Server Error. {API} API server crashed. {url}')
        return f'{variant}: ❌ HTTPError 500: Internal Server Error. {API} API server crashed. Its not your fault. Please try again later.'

    # Handle a 503 Service Unavailable status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 503:
        logger.error(f'{variant}: HTTPError 503: Service Temporarily Unavailable. {API} API is overloaded or down for maintenance. {url}')
        return f'{variant}: ❌ HTTPError 503: Service Unavailable. {API} API is unavailable. Its not your fault. Please try again later.'

    # Handle a 504 Gateway Timeout status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 504:
        logger.error(f'{variant}: HTTPError 504: Gateway Timeout. {API} API took too long to respond.')
        return f'{variant}: ❌ HTTPError 504: Gateway Timeout. {API} API response took too long. Its not your fault. Please try again later.'

    # Handle other HTTPErrors. Log the error and return a message to notify the User.
    else:
        logger.error(f'{variant}: HTTPError: {API} API could not respond to this request: {url}. {e}')
        return f'{variant}: ❌ HTTPError: {API} API unavailable.'



def connection_error(e, variant):
    # Retrieve the cause of the ConnectionError exception.
    cause = e.__cause__
    # Search if the cause comes under the OSError class of exceptions and was due to a poor internet
    # connection (denoted as 101).
    if isinstance(cause, OSError) and cause.errno == 101:
        # Log the ConnectionError.
        logger.error(f'{variant}: There was an error connecting to the internet. {e}')
        # Return a flash message to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User understand where along the API request process failed.
        return f'{variant}: ❌ There was a problem with your internet connection. Please check your WiFi, VPN or ethernet connection.'

    else:
        # Log any other ConnectionError.
        logger.error(f'{variant}: ConnectionError [{cause.errno}]: There was an error connecting with the remote server. {e}')
        # Return a flash message to the function in database_functions.py, so that it can be appended to
        # the file name. This will help the User understand where along the API request process failed.
        return f'{variant}: ❌ There was a problem with your connection with the remote server.'



def remote_connection_error(e, variant, API, url):
    # Log RemoteDisconnected exceptions.
    logger.error(f'{variant}: RemoteDisconnected: {API} server dropped the connection. Request: {url}. {e}')
    # Return a flash message to the function in database_functions.py, so that it can be appended to
    # the file name. This will help the User understand where along the API request process failed.
    return f'{variant}: ❌ {API} server dropped the connection before sending a response.'



def json_decoder_error(e, variant, API, url):
    # Log JSONDecodeError exceptions.
    logger.error(f'{variant}: JSON decode error from {API}: Response was not in JSON format. Request: {url}')
    # Log the exception output message and the response from the query, for debugging.
    logger.debug(f'\n{e}')
    # Return a flash message to the function in database_functions.py, so that it can be appended to the file name.
    # This will help the User understand where along the API request process failed.
    return f'{variant}: ❌ Response from {API} was not in JSON format.'









for attempt in range(7):

    try:
        url = "https://httpstat.us/200?sleep=60000"
        response = requests.get(url)
        # response.raise_for_status()

        data = response.json()

    except RemoteDisconnected as e:

        remote_connection_error(e, 'test', 'test_api', url)


"""

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