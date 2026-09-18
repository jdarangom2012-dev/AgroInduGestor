from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import RagMonthlyQuota, RagQueryLog


class RagQuotaExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class QuotaStatus:
    used: int
    limit: int

    @property
    def remaining(self):
        return max(self.limit - self.used, 0)


def _period_start():
    today = timezone.localdate()
    return today.replace(day=1)


def get_quota_status():
    limit = settings.RAG_MONTHLY_QUERY_LIMIT
    used = (
        RagMonthlyQuota.objects.filter(period_start=_period_start())
        .values_list('used', flat=True)
        .first()
        or 0
    )
    return QuotaStatus(used=used, limit=limit)


@transaction.atomic
def reserve_query(user, question):
    limit = settings.RAG_MONTHLY_QUERY_LIMIT
    quota, _ = RagMonthlyQuota.objects.get_or_create(period_start=_period_start())
    quota = RagMonthlyQuota.objects.select_for_update().get(pk=quota.pk)
    if quota.used >= limit:
        raise RagQuotaExceeded(
            f'Has utilizado las {limit} consultas mensuales del Asistente IA. '
            'Contacta al administrador para activar un plan con más consultas.'
        )

    RagMonthlyQuota.objects.filter(pk=quota.pk).update(used=F('used') + 1)
    return RagQueryLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        quota=quota,
        question=question,
    )


def complete_query(log, operation):
    RagQueryLog.objects.filter(pk=log.pk, status=RagQueryLog.STATUS_PENDING).update(
        status=RagQueryLog.STATUS_SUCCESS,
        operation=operation[:80],
        completed_at=timezone.now(),
    )


@transaction.atomic
def fail_query(log, error):
    locked_log = RagQueryLog.objects.select_for_update().get(pk=log.pk)
    if locked_log.status != RagQueryLog.STATUS_PENDING:
        return
    locked_log.status = RagQueryLog.STATUS_FAILED
    locked_log.error = str(error)[:2000]
    locked_log.completed_at = timezone.now()
    locked_log.save(update_fields=['status', 'error', 'completed_at'])
    RagMonthlyQuota.objects.filter(pk=locked_log.quota_id, used__gt=0).update(
        used=F('used') - 1
    )
