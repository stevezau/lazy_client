# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Imdbcache.votes'
        db.alter_column('imdbcache', 'votes', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Imdbcache.score'
        db.alter_column('imdbcache', 'score', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=3, decimal_places=1))

        # Changing field 'Imdbcache.year'
        db.alter_column('imdbcache', 'year', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'DownloadItem.tvdbid'
        db.alter_column('download', 'tvdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Tvdbcache'], null=True, on_delete=models.DO_NOTHING))

        # Changing field 'DownloadItem.imdbid'
        db.alter_column('download', 'imdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Imdbcache'], null=True, on_delete=models.DO_NOTHING))

        # Changing field 'Tvdbcache.imdbid'
        db.alter_column('tvdbcache', 'imdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Imdbcache'], null=True, on_delete=models.DO_NOTHING))

    def backwards(self, orm):

        # Changing field 'Imdbcache.votes'
        db.alter_column('imdbcache', 'votes', self.gf('django.db.models.fields.IntegerField')())

        # User chose to not deal with backwards NULL issues for 'Imdbcache.score'
        raise RuntimeError("Cannot reverse this migration. 'Imdbcache.score' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Imdbcache.score'
        db.alter_column('imdbcache', 'score', self.gf('django.db.models.fields.DecimalField')(max_digits=3, decimal_places=1))

        # Changing field 'Imdbcache.year'
        db.alter_column('imdbcache', 'year', self.gf('django.db.models.fields.IntegerField')())

        # Changing field 'DownloadItem.tvdbid'
        db.alter_column('download', 'tvdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Tvdbcache'], null=True, on_delete=models.SET_NULL))

        # Changing field 'DownloadItem.imdbid'
        db.alter_column('download', 'imdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Imdbcache'], null=True, on_delete=models.SET_NULL))

        # Changing field 'Tvdbcache.imdbid'
        db.alter_column('tvdbcache', 'imdbid_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazyweb.Imdbcache'], null=True, on_delete=models.SET_NULL))

    models = {
        u'lazyweb.downloaditem': {
            'Meta': {'ordering': "['-id']", 'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ftppath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazyweb.Imdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'localsize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '10', 'null': 'True'}),
            'remotesize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazyweb.Tvdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'})
        },
        u'lazyweb.imdbcache': {
            'Meta': {'object_name': 'Imdbcache', 'db_table': "'imdbcache'"},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'posterimg': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'score': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '3', 'decimal_places': '1', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
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
            'description': ('django.db.models.fields.TextField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazyweb.Imdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'networks': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lazyweb']