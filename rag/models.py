from django.conf import settings
from django.db import models


class RagMonthlyQuota(models.Model):
    period_start = models.DateField(unique=True)
    used = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'rag_monthly_quota'
        ordering = ['-period_start']

    def __str__(self):
        return f'{self.period_start:%Y-%m}: {self.used}'


class RagQueryLog(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_SUCCESS, 'Exitosa'),
        (STATUS_FAILED, 'Fallida'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rag_queries',
    )
    quota = models.ForeignKey(
        RagMonthlyQuota,
        on_delete=models.PROTECT,
        related_name='queries',
    )
    question = models.TextField()
    operation = models.CharField(max_length=80, blank=True, default='')
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rag_query_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='idx_rag_status_created'),
        ]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} · {self.status}'
