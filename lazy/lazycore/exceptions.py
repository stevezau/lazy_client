'''
Created on 14/02/2011

@author: Steve
'''
class AlradyExists(Exception):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """


class AlradyExists_Updated(Exception):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    existingitem = None

    def __init__(self, existingitem):
        self.existingitem = existingitem


class FTPException(Exception):
    """

    """

class DownloadException(Exception):
    """

    """

class XBMCException(Exception):
    """

    """