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


class NoMediaFilesFoundException(Exception):
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

class InvalidFileException(Exception):
    """
    """


class ExtractCRCException(Exception):
    """
    """

    bad_archives = []

    def __init__(self, bad_archives=[]):
        self.bad_archives = bad_archives


class ManuallyFixException(Exception):
    """
    """

    fix_files = []

    def __init__(self, fix_files=[]):
        self.fix_files = fix_files


class RenameException(Exception):
    """
    """

class RenameUnknownException(Exception):
    """
    """

class FTPException(Exception):
    """

    """

class DownloadException(Exception):
    """

    """

class XBMCException(Exception):
    """

    """


class ExtractException(Exception):
    """

    """

