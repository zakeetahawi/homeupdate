from django.contrib import admin

from .models import BoardWidgetSettings


@admin.register(BoardWidgetSettings)
class BoardWidgetSettingsAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "is_active", "order", "target_value"]
    list_editable = ["is_active", "order", "target_value"]
    ordering = ["order"]
