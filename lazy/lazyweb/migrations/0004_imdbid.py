# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        for dlitem in orm.DownloadItem.objects.all():
            if dlitem.imdbid:
                try:
                    dlitem.imdbid = dlitem.imdbid.lstrip("tt")
                    dlitem.save()
                except AttributeError as e:
                  pass

        for imdbcache in orm.Imdbcache.objects.all():
            if imdbcache.imdbid:
                 try:
                    imdbcache.imdbid = imdbcache.imdbid.lstrip("tt")
                    imdbcache.save()
                 except AttributeError as e:
                    pass

        for row in orm.Imdbcache.objects.all():
            if orm.Imdbcache.objects.filter(imdbid=row.imdbid).count() > 1:
                row.delete()

        for row in orm.Tvdbcache.objects.all():
            if orm.Tvdbcache.objects.filter(tvdbid=row.tvdbid).count() > 1:
                row.delete()

    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")

    models = {
        u'lazyweb.downloaditem': {
            'Meta': {'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ftppath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
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
            'tvdbid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazyweb.imdbcache': {
            'Meta': {'object_name': 'Imdbcache', 'db_table': "'imdbcache'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.TextField', [], {}),
            'posterimg': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
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
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'networks': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lazyweb']
    symmetrical = True
