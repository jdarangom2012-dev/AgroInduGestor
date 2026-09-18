from django.contrib import admin

from .models import RagMonthlyQuota, RagQueryLog


@admin.register(RagMonthlyQuota)
class RagMonthlyQuotaAdmin(admin.ModelAdmin):
    list_display = ('period_start', 'used')
    readonly_fields = ('period_start', 'used')


@admin.register(RagQueryLog)
class RagQueryLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'operation', 'status')
    list_filter = ('status', 'operation', 'created_at')
    search_fields = ('question', 'user__username')
    readonly_fields = (
        'user', 'quota', 'question', 'operation', 'status', 'error',
        'created_at', 'completed_at',
    )
