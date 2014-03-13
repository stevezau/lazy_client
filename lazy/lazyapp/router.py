class LazyRouter(object):
    def db_for_read(self, model, **hints):
        "Point all operations on lazycore models to 'lazywebdb'"
        if model._meta.app_label == 'lazycore':
            return 'lazydb'
        return 'default'

    def db_for_write(self, model, **hints):
        "Point all operations on lazycore models to 'lazywebdb'"
        if model._meta.app_label == 'lazycore':
            return 'lazydb'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a both models in lazycore app"
        if obj1._meta.app_label == 'lazycore' and obj2._meta.app_label == 'lazycore':
            return True
        # Allow if neither is lazycore app
        elif 'lazycore' not in [obj1._meta.app_label, obj2._meta.app_label]:
            return True
        return False
    
    def allow_syncdb(self, db, model):
        if db == 'lazywebdb' or model._meta.app_label == "lazycore":
            return False # we're not using syncdb on our legacy database
        else: # but all config models/databases are fine
            return True