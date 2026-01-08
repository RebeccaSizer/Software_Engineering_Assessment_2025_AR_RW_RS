"""
stringify.py: This script converts values returned from
querying an SQL database into strings that can be easily
encoded and downloaded in CSV format. This is particularly
helpful when exporting tables that illustrate the content
from variant databases in CSV format, so that they can be
viewed as intended in Microsoft Excel.
"""

from tools.utils.logger import logger

def stringify(value):
    """
    This function processes values literally by converting them into text strings, so that they can appear appropriately
    in Microsoft Excel.
    This function also accommodates for special characters that have secondary functions in Microsoft Excel that
    might alter the original value parsed from the table: "=", "+", "-", "@", "*"

    :param value: A value displayed in the table viewable by the User on the flask app.
            E.g.: Patient1
                  NC_000001.11:g.7984999T>A
                  NM_007262.5:c.515T>A
                  NP_009193.2:p.(Leu172Gln)
                  PARK7
                  16369
                  Uncertain significance
                  Autosomal recessive early-onset Parkinson disease 7
                  ★
                  criteria provided, single submitter

    :return: string_value: A string of the value from the table viewable by the User on the flask app.
                     E.g.: 'Patient1'
                           'NC_000001.11:g.7984999T>A'
                           'NM_007262.5:c.515T>A	'
                           'NP_009193.2:p.(Leu172Gln)'
                           'PARK7'
                           '16369'
                           'Uncertain significance'
                           'Autosomal recessive early-onset Parkinson disease 7'
                           '★'
                           'criteria provided, single submitter'
    """

    # Log that the values from the table are being converted into strings of those values.
    logger.info(f'The following value from the table is being converted into a string: {value}')

    # Value converted to string.
    string_value = str(value)

    # The values that start with "=", "+", "-", "@", or "*" are prefixed with an apostrophe to prevent Microsoft
    # Excel from computing the value inappropriately.
    if string_value.startswith(("=", "+", "-", "@", "*")):
        return "'" + value

    # Return the string value.
    return string_value