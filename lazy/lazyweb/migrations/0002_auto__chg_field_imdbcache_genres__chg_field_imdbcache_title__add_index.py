# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Imdbcache.genres'
        db.alter_column('imdbcache', 'genres', self.gf('django.db.models.fields.CharField')(max_length=200, null=True))

        # Changing field 'Imdbcache.title'
        db.alter_column('imdbcache', 'title', self.gf('django.db.models.fields.CharField')(max_length=200))
        # Adding index on 'Imdbcache', fields ['title']
        db.create_index('imdbcache', ['title'])


        # Changing field 'Imdbcache.votes'
        db.alter_column('imdbcache', 'votes', self.gf('django.db.models.fields.IntegerField')())

        # Changing field 'Imdbcache.posterimg'
        db.alter_column('imdbcache', 'posterImg', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, db_column='posterImg'))

        # Changing field 'Imdbcache.score'
        db.alter_column('imdbcache', 'score', self.gf('django.db.models.fields.DecimalField')(max_digits=3, decimal_places=1))

        # Changing field 'Imdbcache.year'
        db.alter_column('imdbcache', 'year', self.gf('django.db.models.fields.IntegerField')())

        # Changing field 'Imdbcache.desc'
        db.alter_column('imdbcache', 'desc', self.gf('django.db.models.fields.CharField')(max_length=200, null=True))
        # Deleting field 'DownloadItem.requested'
        db.delete_column('download', 'requested')

        # Deleting field 'DownloadItem.updated'
        db.delete_column('download', 'updated')

        # Deleting field 'DownloadItem.epoverride'
        db.delete_column('download', 'epOverride')

        # Deleting field 'DownloadItem.geteps'
        db.delete_column('download', 'getEps')


        # Changing field 'DownloadItem.dateadded'
        db.alter_column('download', 'dateadded', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.datetime(2013, 12, 15, 0, 0)))
        # Adding index on 'DownloadItem', fields ['dateadded']
        db.create_index('download', ['dateadded'])


        # Changing field 'DownloadItem.title'
        db.alter_column('download', 'title', self.gf('django.db.models.fields.CharField')(max_length=150))
        # Adding index on 'DownloadItem', fields ['title']
        db.create_index('download', ['title'])


        # Changing field 'DownloadItem.section'
        db.alter_column('download', 'section', self.gf('django.db.models.fields.CharField')(max_length=10, null=True))
        # Adding index on 'DownloadItem', fields ['section']
        db.create_index('download', ['section'])


        # Changing field 'DownloadItem.localpath'
        db.alter_column('download', 'localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'DownloadItem.path'
        db.alter_column('download', 'path', self.gf('django.db.models.fields.CharField')(max_length=255))
        # Adding index on 'DownloadItem', fields ['path']
        db.create_index('download', ['path'])


        # Changing field 'DownloadItem.message'
        db.alter_column('download', 'message', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Tvdbcache.title'
        db.alter_column('tvdbcache', 'title', self.gf('django.db.models.fields.CharField')(max_length=200))
        # Adding index on 'Tvdbcache', fields ['title']
        db.create_index('tvdbcache', ['title'])


        # Changing field 'Tvdbcache.posterimg'
        db.alter_column('tvdbcache', 'posterImg', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, db_column='posterImg'))

        # Changing field 'Tvdbcache.genre'
        db.alter_column('tvdbcache', 'genre', self.gf('django.db.models.fields.CharField')(max_length=200, null=True))

        # Changing field 'Tvdbcache.desc'
        db.alter_column('tvdbcache', 'desc', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Tvdbcache.network'
        db.alter_column('tvdbcache', 'network', self.gf('django.db.models.fields.CharField')(max_length=50, null=True))

    def backwards(self, orm):
        # Removing index on 'Tvdbcache', fields ['title']
        db.delete_index('tvdbcache', ['title'])

        # Removing index on 'DownloadItem', fields ['path']
        db.delete_index('download', ['path'])

        # Removing index on 'DownloadItem', fields ['section']
        db.delete_index('download', ['section'])

        # Removing index on 'DownloadItem', fields ['title']
        db.delete_index('download', ['title'])

        # Removing index on 'DownloadItem', fields ['dateadded']
        db.delete_index('download', ['dateadded'])

        # Removing index on 'Imdbcache', fields ['title']
        db.delete_index('imdbcache', ['title'])


        # Changing field 'Imdbcache.genres'
        db.alter_column('imdbcache', 'genres', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Imdbcache.title'
        db.alter_column('imdbcache', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Imdbcache.votes'
        db.alter_column('imdbcache', 'votes', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Imdbcache.posterimg'
        db.alter_column('imdbcache', 'posterImg', self.gf('django.db.models.fields.TextField')(null=True, db_column='posterImg'))

        # Changing field 'Imdbcache.score'
        db.alter_column('imdbcache', 'score', self.gf('django.db.models.fields.FloatField')())

        # Changing field 'Imdbcache.year'
        db.alter_column('imdbcache', 'year', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Imdbcache.desc'
        db.alter_column('imdbcache', 'desc', self.gf('django.db.models.fields.TextField')(null=True))
        # Adding field 'DownloadItem.requested'
        db.add_column('download', 'requested',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'DownloadItem.updated'
        db.add_column('download', 'updated',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'DownloadItem.epoverride'
        db.add_column('download', 'epoverride',
                      self.gf('django.db.models.fields.IntegerField')(null=True, db_column='epOverride', blank=True),
                      keep_default=False)

        # Adding field 'DownloadItem.geteps'
        db.add_column('download', 'geteps',
                      self.gf('django.db.models.fields.TextField')(null=True, db_column='getEps', blank=True),
                      keep_default=False)


        # Changing field 'DownloadItem.dateadded'
        db.alter_column('download', 'dateadded', self.gf('django.db.models.fields.DateTimeField')(null=True))

        # Changing field 'DownloadItem.title'
        db.alter_column('download', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'DownloadItem.section'
        db.alter_column('download', 'section', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'DownloadItem.localpath'
        db.alter_column('download', 'localpath', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'DownloadItem.path'
        db.alter_column('download', 'path', self.gf('django.db.models.fields.TextField')())

        # Changing field 'DownloadItem.message'
        db.alter_column('download', 'message', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

        # Changing field 'Tvdbcache.title'
        db.alter_column('tvdbcache', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Tvdbcache.posterimg'
        db.alter_column('tvdbcache', 'posterImg', self.gf('django.db.models.fields.TextField')(null=True, db_column='posterImg'))

        # Changing field 'Tvdbcache.genre'
        db.alter_column('tvdbcache', 'genre', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Tvdbcache.desc'
        db.alter_column('tvdbcache', 'desc', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Tvdbcache.network'
        db.alter_column('tvdbcache', 'network', self.gf('django.db.models.fields.TextField')(null=True))

    models = {
        u'lazyweb.downloaditem': {
            'Meta': {'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'imdbID'", 'blank': 'True'}),
            'lftppid': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'localsize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '10', 'null': 'True'}),
            'remotesize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazyweb.imdbcache': {
            'Meta': {'object_name': 'Imdbcache', 'db_table': "'imdbcache'"},
            'desc': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.TextField', [], {}),
            'posterimg': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_column': "'posterImg'", 'blank': 'True'}),
            'score': ('django.db.models.fields.DecimalField', [], {'max_digits': '3', 'decimal_places': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'year': ('django.db.models.fields.IntegerField', [], {'default': '0'})
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
            'desc': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'genre': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'network': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'db_column': "'posterImg'", 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lazyweb']