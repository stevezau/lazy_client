#!/usr/bin/python2.7
import logging
import pprint

import tvdb_api

from lazy.includes.manager import config
from lazy.includes.manager import Session
from lazy.includes.schemadef import ImdbCache
from lazy.includes.schemadef import DownloadItem, TVDBCache
from lazy.includes.ftpmanager import FTPManager

logger = logging.getLogger('MoveMovie')


class test:
    
    def __init__(self, parentParser):
        global config
        self.__config = config




    def execute(self):

        session = Session()

        query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_NEW)
        results = query.all()

        ftpManager = FTPManager()

        for dlItem in results:

            if dlItem.getEps is not None and dlItem.getEps != '':



                ftpManager.mirrorMulti(dlItem.localpath, getFolders, dlItem.id)



