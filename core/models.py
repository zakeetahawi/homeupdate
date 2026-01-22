from django.db import models
from django.utils.translation import gettext_lazy as _


class RecycleBin(models.Model):
    """
    Unmanaged model for Global Recycle Bin Dashboard.
    This model doesn't have a database table - it's used only for Admin UI.
    """
    
    class Meta:
        managed = False
        verbose_name = _("سلة المحذوفات")
        verbose_name_plural = _("سلة المحذوفات")
        app_label = 'core'
