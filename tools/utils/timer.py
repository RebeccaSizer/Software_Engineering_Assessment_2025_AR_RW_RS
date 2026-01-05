"""
timer.py: This script provides a decorator to other functions,
that time how long those functions take to return a value.
The time a function takes to complete is reported in a
logger message.

This is particularly helpful for timing functions that take
longer to reach a return, such as those that download large
amount of information from external resources:
    - clinvar_vs_download downloads variant summary records
      from ClinVar.
    - fetch_vv and get_mane_nc queries the VariantValidator
      API.
"""

import time
from tools.utils.logger import logger

def timer(func):
    '''
    This function was created to time how long a function takes to complete.

    :params: func: A function in a script.
             E.g.: def func():

    output: result: The time is takes to complete the function.
                E.g.: "func took 127.0602 seconds"

    :command: @timer
              def func():
    '''

    def wrapper(*args, **kwargs):
        '''
        This function creates a wrapper around a function to apply the timer.
        It replaces the function that it is supposed to time, extracts the arguments of that function and uses them in
        the original function, within the wrapper's script.
        The time if logged.

        :params: *args: Arguments to pass to the function.
                  E.g.: variable_x, variable_y

              **kwargs: Keyword arguments to pass to the function.
                  E.g.: Path=None, a=True, b=2

        :output: result: The output of the original function.
                  E.g.: x = 5
                        y = 2
                        def func(x, y, a=True):
                            if a is True:
                                return x + y
                        result = 7

        :command: invoked by the @timer wrapper above the function.
        '''

        # Start the timer.
        start = time.perf_counter()

        # Implement the original function.
        result = func(*args, **kwargs)

        # Stop the timer.
        end = time.perf_counter()

        # Log how long the process took to complete.
        logger.debug(f"{func.__name__} took {end - start:.4f} seconds")

        # Returns the result of the original function.
        return result

    # returns back to Python.
    return wrapper