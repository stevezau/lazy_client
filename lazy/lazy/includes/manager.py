#!/usr/bin/python
import os
import logging
import ConfigParser
from ConfigParser import NoOptionError

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool

from lazy.includes import functions, schemadef
from lazy.includes.simpleconfigparser import simpleconfigparser

logger = logging.getLogger('Lazy Manager')

Session = sessionmaker()
manager = None

global config


class Manager(object):

    lazy_home = None
    lftpPath = None
    ftpHost = None
    ftpUserName = None
    ftpPwd = None
    ftpPort = None
    lazy_exec = None
    ignore_file = None
    download_images = None
    approved_file = None
    tvshowsPath = None
    showMappings = None
    tvdbAccountID = None
    
    mainArgs = None

    def __init__(self, mainArgs):
        global manager, config
        assert not manager, 'Only one instance of Manager should be created at a time!'
        manager = self

        self.mainArgs = mainArgs

        self.setupLogging()
        self.setupConfig()

        self.setupDB()

        
    def setupDB(self):
        global config
        dbFile = None
        
        try:
            dbFile = config.get("general", "db")
        except NoOptionError:
            pass

        dbFile = os.path.join(self.lazy_home, 'lazy.db')

        dbFile = os.path.expanduser(dbFile)
        dbFile = os.path.abspath(dbFile)
               
        connection = 'sqlite:///%s' % dbFile

        # fire up the engine
        logger.debug('connecting to: %s' % connection)
        try:
            self.engine = create_engine(connection, poolclass=SingletonThreadPool)
        except ImportError:
            functions.raiseError(logger, 'FATAL: Unable to use SQLite. Are you running Python 2.5.x or 2.6.x ?\n'
            'Python should normally have SQLite support built in.\n'
            'If you\'re running correct version of Python then it is not equipped with SQLite.\n'
            'Try installing `pysqlite` and / or if you have compiled python yourself, recompile it with SQLite support.')

        Session.configure(bind=self.engine)

        #Load schema
        schemadef.loadSchema(self.engine)
        
        
    def setupLogging(self):
        global config

        # Setup Logging
        if self.mainArgs.logFile:
            self.logFile = self.mainArgs.logFile
        else:
            self.logFile = 'lazy.log' 
        
        if self.mainArgs.debug:
            logLevel = logging.DEBUG
        else:
            logLevel = logging.INFO
        
        logging.RootLogger.setLevel(logging.root, logLevel)
        
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        logging.root.addHandler(ch)
    
    def __del__(self):
        global manager
        manager = None

    def ckConfigItem(self, section, var):
        logger.debug("Checking config item %s" % var)
        configItem = config.get(section, var)

        if configItem is None or configItem == '':
            functions.raiseError(logger, "Config item is missing %s" % var)

        return configItem

    def setupConfig(self):
        global config

        # Load Lazy Manager
        if self.mainArgs.configFile:
            confFile = self.mainArgs.configFile
        else:
            confFile = os.path.expanduser('~/.lazy/config.cfg')

        if not os.path.isfile(confFile):
            functions.raiseError(logger, "Config file does not exist: %s" % confFile)

        config = simpleconfigparser()

        config.readfp(open(confFile))


        self.lazy_home = self.ckConfigItem('general', 'lazy_home')

        if not os.path.isdir(self.lazy_home):
            functions.raiseError(logger, "Lazy Home does not exist: %s" % self.lazy_home)

        self.lazy_exec = self.ckConfigItem('general', 'lazy_exec')

        if not os.path.isfile(self.lazy_exec):
            functions.raiseError(logger, "Lazy Exec does not exist: %s" % self.lazy_exec)

        self.lftpPath = self.ckConfigItem('general', 'lftp')

        if not os.path.isfile(self.lftpPath):
            functions.raiseError(logger, "LFTP exec location in correct or not installed.. check it exists: " . self.lftpPath)

        self.ftpHost = self.ckConfigItem('ftp', 'ftp_ip')
        self.ftpPort = self.ckConfigItem('ftp', 'ftp_port')
        self.ftpUserName = self.ckConfigItem('ftp', 'ftp_user')
        self.ftpPwd = self.ckConfigItem('ftp', 'ftp_pass')

        self.ignore_file = self.ckConfigItem('general', 'ignore_file')

        if not os.path.isfile(self.ignore_file):
            functions.raiseError(logger, "Ignore file does not exist: %s" % self.ignore_file)

        self.approved_file = self.ckConfigItem('general', 'approved_file')

        if not os.path.isfile(self.approved_file):
            functions.raiseError(logger, "Approved file does not exist: %s" % self.approved_file)

        self.download_images = self.ckConfigItem('general', 'download_images')

        if not os.path.isdir(self.download_images):
            functions.raiseError(logger, "Download Images folder does does not exist: " . self.download_images)

        self.tvshowsPath = self.ckConfigItem('sections', 'TV')

        self.tvdbAccountID = self.ckConfigItem('general', 'tvdb_accountid')

        self.showMappings = config.items('TVShowID')
