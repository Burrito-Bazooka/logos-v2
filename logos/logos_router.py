# LogosRouter.py

import logging
from django.conf import settings
from django.db.models import Count

logger = logging.getLogger(__name__)
logging.config.dictConfig(settings.LOGGING)

            
class LogosRouter(object):
    def db_for_read(self, model, **hints):
        """
        Select DB to read from
        """
        for app in settings.INSTALLED_APPS:
            mod = __import__(app)
            try:
                if hasattr(mod.models, 'DB_ROUTER'):
                    for k, models in mod.models.DB_ROUTER.iteritems():
                        for model_name in models:
                            if model.__name__ == model_name:
                                return k
            except AttributeError:
                pass  # pass on missing models attribute
        return 'default'
        
    
       
    def db_for_write(self, model, **hints):
        """
        Select DB to write to
        """

        for app in settings.INSTALLED_APPS:
            mod = __import__(app)
            try:
                if hasattr(mod.models, 'DB_ROUTER'):
                    for k, models in mod.models.DB_ROUTER.iteritems():
                        for model_name in models:
                            if model.__name__ == model_name:
                                return k
            except AttributeError:
                pass  # pass on missing models attribute
        return 'default'
        
        

    def allow_relation(self, obj1, obj2, **hints):
        """
        No opinion
        """
        return None

    def allow_migrate(self, db, model):
        """
        Whether to allow data migrations on this model
        manage.py loaddata seems to not work without this
        """
        for app in settings.INSTALLED_APPS:
            mod = __import__(app)
            try:
                if hasattr(mod.models, 'DB_ROUTER'):
                    for k, models in mod.models.DB_ROUTER.iteritems():
                        for model_name in models:
                            if model.__name__ == model_name:
                                if db == k:
                                    return True
                                else:
                                    return False
                                    
            except AttributeError:
                pass  # pass on missing models attribute

        
        if db == 'default':
            return True
        else:
            return False 
