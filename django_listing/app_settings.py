#
# Created : 2020-07-24
#
# @author: Eric Lapouyade
#
from django.conf import settings

class AppSettings:
    HEADER_TEMPLATE = 'django_listing/header.html'
    FOOTER_TEMPLATE = 'django_listing/footer.html'
    DATETIMEPICKER_CSS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.min.css'
    DATETIMEPICKER_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.full.min.js'
    DROPZONE_CSS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/dropzone/5.7.2/dropzone.min.css'
    DROPZONE_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/dropzone/5.7.2/dropzone.min.js'

    def __init__(self):
        if hasattr(settings, 'DJANGO_LISTING'):
            self.__dict__.update(settings.DJANGO_LISTING)
        self.context = { k:getattr(self, k) for k in dir(self) if k.isupper() }


app_settings = AppSettings()


