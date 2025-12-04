import time
from tools.utils.logger import logger

def request_status_codes(e, variant, url, API, attempt):

    # Handle a 400 Bad Requests status error code. Log the error and return a message to notify the User.
    if e.response.status_code == 400:
        logger.error(f'{variant}: HTTPError 400: Bad Request. {API} API could not process the request: {url}.\n{e}', exc_info=True)
        return f'{variant}: ❌ HTTPError 400: Bad Request. {API} API did not accept this variant description.'

    # Handle a 404 Not Found status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 404:
        logger.error(f'{variant}: HTTPError 404: Not Found. {API} API could not locate an endpoint from the request: {url}.\n{e}', exc_info=True)
        return f'{variant}: ❌ HTTPError 404: Not Found. {API} API could not find a response to this variant description.'

    # Handle a 408 Request Timeout status error code
    elif e.response.status_code == 408:

        if attempt < 4:
            # Create a delay between attempts if 408 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(f'{variant}: HTTPError 408: Request Timeout. Request cannot reach {API} server: {url}{e}', exc_info=True)
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/5')

        else:
            logger.error(f'{variant}: HTTPError 408 status: Request Timeout. Request did not reach {API} server: {url}.\n{e}', exc_info=True)
            return f'{variant}: ❌ HTTPError 408: {API} could not be queried. Please try again later.'

    # Handle a 429 Too Many Requests status error code
    elif e.response.status_code == 429:

        if attempt < 5:
            # Create a delay between attempts if 429 error is raised.
            time.sleep(2 ** attempt)
            # Log a warning if another request needs to be sent.
            logger.warning(f'{variant}: HTTPError 429: Too Many Requests. {API} is currently overloaded with requests.\n{e}', exc_info=True)
            # Log a description of which attempt out of 5 is going to be tried.
            logger.info(f'{variant}: Trying to retrieve variant information from {API} again. Attempt: {attempt + 2}/5')

        else:
            logger.error(f'{variant}: HTTPError 429 persisted: Too Many Requests. {API} was overloaded with requests: {url}.\n{e}', exc_info=True)
            return f'{variant}: ❌ HTTPError 429: {API} is currently overloaded with requests. Please try again later.'

    # Handle a 500 Internal Server Error status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 500:
        logger.error(f'{variant}: HTTPError 500: Internal Server Error. {API} API server crashed.\n{e}', exc_info=True)
        return f'{variant}: ❌ HTTPError 500: Internal Server Error. {API} API is not working. Its not your fault. Please try again later.'

    # Handle a 503 Service Unavailable status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 503:
        logger.error(f'{variant}: HTTPError 503: Service Unavailable. {API} API is overloaded or down for maintenance.\n{e}', exc_info=True)
        return f'{variant}: ❌ HTTPError 503: Service Unavailable. {API} API is not working. Its not your fault. Please try again later.'

    # Handle a 504 Gateway Timeout status error code. Log the error and return a message to notify the User.
    elif e.response.status_code == 504:
        logger.error(f'{variant}: HTTPError 504: Gateway Timeout. {API} API took too long to respond.\n{e}', exc_info=True)
        return f'{variant}: ❌ HTTPError 504: Gateway Timeout. {API} API response took too long. Its not your fault. Please try again later.'

    # Handle other HTTPErrors. Log the error and return a message to notify the User.
    else:
        logger.error(f'{variant}: {API} API could not respond using request: {url}\nHTTPError: {e}', exc_info=True)
        return f'{variant}: ❌ HTTPError: {API} API unavailable.'


