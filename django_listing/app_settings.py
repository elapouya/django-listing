#
# Created : 2020-07-24
#
# @author: Eric Lapouyade
#
from django.conf import settings
from django.utils.safestring import mark_safe


class AppSettings:
    HEADER_TEMPLATE = 'django_listing/header.html'
    FOOTER_TEMPLATE = 'django_listing/footer.html'
    DATETIMEPICKER_CSS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.min.css'
    DATETIMEPICKER_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.full.min.js'
    DROPZONE_CSS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/dropzone/5.7.2/dropzone.min.css'
    DROPZONE_JS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/dropzone/5.7.2/dropzone.js'
    DROPZONE_PARAMS = dict(
        params={'force_action':'upload'}, # this parameter is mandatory to have upload button working
        clickable=mark_safe('"#" + listing_div_id + " .button-action-upload"'), # listing_div_id is defined in footer.html
        init=mark_safe("""function() {
            var ajax_error=false;
            this.on("error", function() { ajax_error=true; });
            this.on("queuecomplete", function(e) {
                if (! ajax_error) {
                    document.location.reload(true);
                }
            });
            }"""),
    )
    STATIC_URL = settings.STATIC_URL
    MEDIA_URL = settings.MEDIA_URL

    def __init__(self):
        if hasattr(settings, 'DJANGO_LISTING'):
            for k,v in settings.DJANGO_LISTING.items():
                if k.isupper() and hasattr(self, k):
                    if isinstance(v, dict):
                        setattr(self, k, { **getattr(self,k), **v })
                    else:
                        setattr(self, k, v)
        self.context = { k:getattr(self, k) for k in dir(self) if k.isupper() }


app_settings = AppSettings()


