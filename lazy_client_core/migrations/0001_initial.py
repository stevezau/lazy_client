# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TVShowMappings'
        db.create_table('tvshowmappings', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=150, db_index=True)),
            ('tvdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'], on_delete=models.DO_NOTHING)),
        ))
        db.send_create_signal(u'lazy_client_core', ['TVShowMappings'])

        # Adding model 'DownloadItem'
        db.create_table('download', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=150, null=True, blank=True)),
            ('section', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=10, null=True, blank=True)),
            ('ftppath', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('pid', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('retries', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('dateadded', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('dlstart', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('remotesize', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('priority', self.gf('django.db.models.fields.IntegerField')(default=10, null=True)),
            ('requested', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('localsize', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('imdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.Imdbcache'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('tvdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.TVShow'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('epoverride', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('seasonoverride', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('onlyget', self.gf('lazy_client_core.utils.jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'lazy_client_core', ['DownloadItem'])

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
        ))
        db.send_create_signal(u'lazy_client_core', ['Imdbcache'])

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
        db.send_create_signal(u'lazy_client_core', ['Job'])

        # Adding model 'Tvdbcache'
        db.create_table('tvdbcache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('posterimg', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('networks', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('genres', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=255, null=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('imdbid', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lazy_client_core.Imdbcache'], null=True, on_delete=models.DO_NOTHING, blank=True)),
            ('localpath', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'lazy_client_core', ['Tvdbcache'])


    def backwards(self, orm):
        # Deleting model 'TVShowMappings'
        db.delete_table('tvshowmappings')

        # Deleting model 'DownloadItem'
        db.delete_table('download')

        # Deleting model 'Movie'
        db.delete_table('imdbcache')

        # Deleting model 'Job'
        db.delete_table('jobs')

        # Deleting model 'Tvdbcache'
        db.delete_table('tvdbcache')


    models = {
        u'lazy_client_core.downloaditem': {
            'Meta': {'ordering': "['id']", 'object_name': 'DownloadItem', 'db_table': "'download'"},
            'dateadded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'dlstart': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'epoverride': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'ftppath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazy_client_core.Imdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'localsize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'onlyget': ('lazy_client_core.utils.jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '10', 'null': 'True'}),
            'remotesize': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'requested': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'seasonoverride': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazy_client_core.Tvdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'})
        },
        u'lazy_client_core.imdbcache': {
            'Meta': {'object_name': 'Imdbcache', 'db_table': "'imdbcache'"},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'posterimg': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'score': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '3', 'decimal_places': '1', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
        },
        u'lazy_client_core.job': {
            'Meta': {'object_name': 'Job', 'db_table': "'jobs'"},
            'finishdate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'report': ('lazy_client_core.utils.jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'startdate': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazy_client_core.tvdbcache': {
            'Meta': {'object_name': 'Tvdbcache', 'db_table': "'tvdbcache'"},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'genres': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazy_client_core.Imdbcache']", 'null': 'True', 'on_delete': 'models.DO_NOTHING', 'blank': 'True'}),
            'localpath': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'networks': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'posterimg': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lazy_client_core.tvshowmappings': {
            'Meta': {'ordering': "['-id']", 'object_name': 'TVShowMappings', 'db_table': "'tvshowmappings'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150', 'db_index': 'True'}),
            'tvdbid': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['lazy_client_core.Tvdbcache']", 'on_delete': 'models.DO_NOTHING'})
        }
    }

    complete_apps = ['lazy_client_core']