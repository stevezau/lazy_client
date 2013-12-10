'''
Created on 14/02/2011

@author: Steve
'''
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class LazyError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """



    def __init__(self, msg, id):
        self.msg = msg
        self.id = id


class FTPError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """



    def __init__(self, msg):
        self.msg = msg
