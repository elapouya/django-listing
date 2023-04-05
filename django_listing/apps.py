from django.apps import AppConfig
from django.utils.safestring import mark_safe


class DjangoListingConfig(AppConfig):
    name = 'django_listing'
    verbose_name = 'django-listing'

    THEME = 'bootstrap4'
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

    def ready(self):
        from django.conf import settings
        from django_listing.theme_config import ThemeConfigMeta, ThemeConfigBase
        from .exceptions import InvalidListingConfiguration
        from django_listing import __version__
        import time

        if hasattr(settings, 'DJANGO_LISTING'):
            for k,v in settings.DJANGO_LISTING.items():
                if k.isupper() and hasattr(self, k):
                    if isinstance(v, dict):
                        setattr(self, k, { **getattr(self,k), **v })
                    else:
                        setattr(self, k, v)
        self.context = { k:getattr(self, k) for k in dir(self) if k.isupper() }
        if isinstance(self.THEME, str):
            self.theme_config = ThemeConfigMeta.get_class(self.THEME)
        elif issubclass(self.THEME, ThemeConfigBase):
            self.theme_config = self.THEME
        else:
            raise InvalidListingConfiguration(
                'THEME parameter must contain either a string '
                'either a class derivated from ThemeConfigBase'
            )
        STATIC_FILES_VERSION = __version__
        if settings.DEBUG:
            STATIC_FILES_VERSION += f"_{time.perf_counter()}"
        self.context.update(
            theme_config=self.theme_config,
            STATIC_URL=settings.STATIC_URL,
            STATIC_FILES_VERSION=STATIC_FILES_VERSION,
        )
        settings.django_listing_settings = self
