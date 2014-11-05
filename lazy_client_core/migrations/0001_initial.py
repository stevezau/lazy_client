# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Version'
        db.create_table('version', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('version', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'lazy_client_core', ['Version'])

        # Adding model 'TVShowMappings'
        db.create_table('tvshowmappings', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=150, db_index=True)),
            ('tvdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'])),
        ))
        db.send_create_signal('lazy_client_core', ['TVShowMappings'])

        # Adding model 'TVShowGenres'
        db.create_table('tvshow_genres', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('genre', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.GenreNames'])),
            ('tvdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'])),
        ))
        db.send_create_signal('lazy_client_core', ['TVShowGenres'])

        # Adding model 'GenreNames'
        db.create_table('genre_names', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('genre', self.gf('lazy_client_core.utils.common.LowerCaseCharField')(unique=True, max_length=150, db_index=True)),
            ('genre_orig', self.gf('django.db.models.fields.CharField')(max_length=150, db_index=True)),
        ))
        db.send_create_signal('lazy_client_core', ['GenreNames'])

        # Adding model 'TVShowNetworks'
        db.create_table('tvshow_networks', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('network', self.gf('lazy_client_core.utils.common.LowerCaseCharField')(unique=True, max_length=150, db_index=True)),
            ('network_orig', self.gf('django.db.models.fields.CharField')(max_length=150, db_index=True)),
        ))
        db.send_create_signal('lazy_client_core', ['TVShowNetworks'])

        # Adding model 'TVShow'
        db.create_table('tvdbcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('posterimg', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('genres', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=255, null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('imdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.Movie'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('ignored', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('favorite', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('fix_report', self.gf('picklefield.fields.PickledObjectField')()),
            ('fix_jobid', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('network', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShowNetworks'], null=True, blank=True)),
        ))
        db.send_create_signal('lazy_client_core', ['TVShow'])

        # Adding model 'Movie'
        db.create_table('imdbcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('score', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=3, decimal_places=1, blank=True)),
            ('votes', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('genres', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('posterimg', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('ignored', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lazy_client_core', ['Movie'])

        # Adding model 'DownloadItem'
        db.create_table('download', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=150, null=True, blank=True)),
            ('section', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=10, null=True, blank=True)),
            ('ftppath', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('pid', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('type', self.gf('django.db.models.fields.IntegerField')(default=3, blank=True)),
            ('taskid', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('retries', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('dateadded', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('dlstart', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('remotesize', self.gf('django.db.models.fields.BigIntegerField')(default=0, null=True)),
            ('priority', self.gf('django.db.models.fields.IntegerField')(default=5, null=True)),
            ('requested', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('localsize', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('message', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('imdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.Movie'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('tvdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('onlyget', self.gf('lazy_client_core.utils.jsonfield.fields.JSONField')(null=True, blank=True)),
            ('video_files', self.gf('lazy_client_core.utils.jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('lazy_client_core', ['DownloadItem'])

        # Adding model 'DownloadLog'
        db.create_table('download_log', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('download_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.DownloadItem'], null=True, blank=True)),
            ('tvshow_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'], null=True, blank=True)),
            ('job_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.Job'], null=True, blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('lazy_client_core', ['DownloadLog'])

        # Adding model 'Job'
        db.create_table('jobs', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('startdate', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('finishdate', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('report', self.gf('lazy_client_core.utils.jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('lazy_client_core', ['Job'])


    def backwards(self, orm):
        # Deleting model 'Version'
        db.delete_table('version')

        # Deleting model 'TVShowMappings'
        db.delete_table('tvshowmappings')

        # Deleting model 'TVShowGenres'
        db.delete_table('tvshow_genres')

        # Deleting model 'GenreNames'
        db.delete_table('genre_names')

        # Deleting model 'TVShowNetworks'
        db.delete_table('tvshow_networks')

        # Deleting model 'TVShow'
        db.delete_table('tvdbcache')

        # Deleting model 'Movie'
        db.delete_table('imdbcache')

        # Deleting model 'DownloadItem'
        db.delete_table('download')

        # Deleting model 'DownloadLog'
        db.delete_table('download_log')

        # Deleting model 'Job'
        db.delete_table('jobs')


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