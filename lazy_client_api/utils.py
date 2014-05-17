__author__ = 'steve'

from rest_framework import status
from rest_framework.response import Response

from rest_framework.views import exception_handler
from lazy_client_core.exceptions import AlradyExists


def custom_exception_handler(exc):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc)

    if isinstance(exc, AlradyExists):
        return Response({'detail': 'already exists'},
                        status=status.HTTP_202_ACCEPTED)

    return response