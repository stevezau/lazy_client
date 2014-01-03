# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadItem'
        db.create_table('download', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('section', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('path', self.gf('django.db.models.fields.TextField')()),
            ('localpath', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('lftppid', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('retries', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('dateadded', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('dlstart', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('remotesize', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('priority', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('localsize', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('imdbid', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='imdbID', blank=True)),
            ('tvdbid', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('epoverride', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='epOverride', blank=True)),
            ('requested', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('geteps', self.gf('django.db.models.fields.TextField')(null=True, db_column='getEps', blank=True)),
        ))
        db.send_create_signal(u'lazyweb', ['DownloadItem'])

        # Adding model 'Imdbcache'
        db.create_table('imdbcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('score', self.gf('django.db.models.fields.FloatField')()),
            ('imdbid', self.gf('django.db.models.fields.TextField')()),
            ('votes', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('genres', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('posterimg', self.gf('django.db.models.fields.TextField')(null=True, db_column='posterImg', blank=True)),
            ('desc', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'lazyweb', ['Imdbcache'])

        # Adding model 'Job'
        db.create_table('jobs', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('outfile', self.gf('django.db.models.fields.TextField')(null=True, db_column='outFile', blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('startdate', self.gf('django.db.models.fields.DateTimeField')(null=True, db_column='startDate', blank=True)),
            ('finishdate', self.gf('django.db.models.fields.DateTimeField')(null=True, db_column='finishDate', blank=True)),
            ('title', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'lazyweb', ['Job'])

        # Adding model 'Tvdbcache'
        db.create_table('tvdbcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('tvdbid', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('network', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('genre', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('desc', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('posterimg', self.gf('django.db.models.fields.TextField')(null=True, db_column='posterImg', blank=True)),
        ))
        db.send_create_signal(u'lazyweb', ['Tvdbcache'])


    def backwards(self, orm):
        # Deleting model 'DownloadItem'
        db.delete_table('download')

        # Deleting model 'Imdbcache'
        db.delete_table('imdbcache')

        # Deleting model 'Job'
        db.delete_table('jobs')

        # Deleting model 'Tvdbcache'
        db.delete_table('tvdbcache')


    models = {
        u'lazyweb.downloaditem': {
            'Meta': {'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'epoverride': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'epOverride'", 'blank': 'True'}),
            'geteps': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'getEps'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'imdbID'", 'blank': 'True'}),
            'lftppid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'localsize': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'path': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'remotesize': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'requested': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'tvdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazyweb.imdbcache': {
            'Meta': {'object_name': 'Imdbcache', 'db_table': "'imdbcache'"},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.TextField', [], {}),
            'posterimg': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'posterImg'", 'blank': 'True'}),
            'score': ('django.db.models.fields.FloatField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazyweb.job': {
            'Meta': {'object_name': 'Job', 'db_table': "'jobs'"},
            'finishdate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_column': "'finishDate'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'outfile': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'outFile'", 'blank': 'True'}),
            'startdate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_column': "'startDate'", 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazyweb.tvdbcache': {
            'Meta': {'object_name': 'Tvdbcache', 'db_table': "'tvdbcache'"},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'genre': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'network': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'posterImg'", 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'tvdbid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lazyweb']