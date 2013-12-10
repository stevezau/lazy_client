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
    
    mainArgs = None

    def __init__(self, mainArgs):
        global manager, config
        assert not manager, 'Only one instance of Manager should be created at a time!'
        manager = self

        self.mainArgs = mainArgs

        self.setupLogging()
        self.setupConfig()
        self.lazyPath = config.get("general", "lazy_home")

        self.setupDB()

        
    def setupDB(self):
        global config
        dbFile = None
        
        try:
            dbFile = config.get("general", "db")
        except NoOptionError:
            pass

        dbFile = os.path.join(self.lazyPath, 'lazy.db')

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

    def setupConfig(self):
        global config

        
        # Load Lazy Manager
        if self.mainArgs.configFile:
            confFile = self.mainArgs.configFile
        else:
            confFile = os.path.expanduser('~/.lazy/config.cfg')

        config = simpleconfigparser()

        config.readfp(open(confFile))
        
        # read the ftp configurations for all sites
        #ftp_site = 1
        #while config.has_section("ftp" + str(ftp_site)):
        #    print "ftp%s settings" % str(ftp_site)
        #    print config.items("ftp" + str(ftp_site))
        #    ftp_site += 1
