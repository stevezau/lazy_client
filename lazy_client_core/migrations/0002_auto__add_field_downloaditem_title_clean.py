# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DownloadItem.title_clean'
        db.add_column('download', 'title_clean',
                      self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DownloadItem.title_clean'
        db.delete_column('download', 'title_clean')


    models = {
        'lazy_client_core.downloaditem': {
            'Meta': {'ordering': "['id']", 'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ftppath': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.Movie']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'localsize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'onlyget': ('lazy_client_core.utils.jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '5', 'null': 'True'}),
            'remotesize': ('django.db.models.fields.BigIntegerField', [], {'default': '0', 'null': 'True'}),
            'requested': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'section': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'taskid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'title_clean': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.TVShow']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '3', 'blank': 'True'}),
            'video_files': ('lazy_client_core.utils.jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'})
        },
        'lazy_client_core.downloadlog': {
            'Meta': {'object_name': 'DownloadLog', 'db_table': "'download_log'"},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'download_id': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.DownloadItem']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job_id': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.Job']", 'null': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tvshow_id': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.TVShow']", 'null': 'True', 'blank': 'True'})
        },
        'lazy_client_core.genrenames': {
            'Meta': {'ordering': "['-id']", 'object_name': 'GenreNames', 'db_table': "'genre_names'"},
            'genre': ('lazy_client_core.utils.common.LowerCaseCharField', [], {'unique': 'True', 'max_length': '150', 'db_index': 'True'}),
            'genre_orig': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'lazy_client_core.job': {
            'Meta': {'object_name': 'Job', 'db_table': "'jobs'"},
            'finishdate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'report': ('lazy_client_core.utils.jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'startdate': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'lazy_client_core.movie': {
            'Meta': {'object_name': 'Movie', 'db_table': "'imdbcache'"},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ignored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'score': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '3', 'decimal_places': '1', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
        },
        'lazy_client_core.tvshow': {
            'Meta': {'object_name': 'TVShow', 'db_table': "'tvdbcache'"},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'favorite': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fix_jobid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'fix_report': ('picklefield.fields.PickledObjectField', [], {}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ignored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.Movie']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.TVShowNetworks']", 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'lazy_client_core.tvshowgenres': {
            'Meta': {'ordering': "['-id']", 'object_name': 'TVShowGenres', 'db_table': "'tvshow_genres'"},
            'genre': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.GenreNames']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.TVShow']"})
        },
        'lazy_client_core.tvshowmappings': {
            'Meta': {'ordering': "['-id']", 'object_name': 'TVShowMappings', 'db_table': "'tvshowmappings'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lazy_client_core.TVShow']"})
        },
        'lazy_client_core.tvshownetworks': {
            'Meta': {'ordering': "['-id']", 'object_name': 'TVShowNetworks', 'db_table': "'tvshow_networks'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'network': ('lazy_client_core.utils.common.LowerCaseCharField', [], {'unique': 'True', 'max_length': '150', 'db_index': 'True'}),
            'network_orig': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'})
        },
        u'lazy_client_core.version': {
            'Meta': {'object_name': 'Version', 'db_table': "'version'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['lazy_client_core']