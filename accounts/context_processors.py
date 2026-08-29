# -*- coding: utf-8 -*-
"""
Context processor: передаёт в шаблоны флаги доступа по ролям.

Используется в шаблонах для показа/скрытия разделов меню и кнопок.
"""
from .access import has_role, user_roles
from .roles import (ATTESTATION_EDIT, ATTESTATION_MGMT, CONTINGENT_EDIT,
                    HR_MGMT, HR_VIEW, INTEGRATION_MGMT, JOURNAL_EDIT,
                    LOW_PERF_VIEW, REPORTING_EDIT, SCHEDULE_EDIT)


def roles_context(request):
    user = request.user
    return {
        'user_roles': user_roles(user),
        'can_manage_contingent': has_role(user, CONTINGENT_EDIT),
        'can_edit_journal': has_role(user, JOURNAL_EDIT),
        'can_view_low_perf': has_role(user, LOW_PERF_VIEW),
        'can_edit_attestation': has_role(user, ATTESTATION_EDIT),
        'can_manage_attestation': has_role(user, ATTESTATION_MGMT),
        'can_edit_schedule': has_role(user, SCHEDULE_EDIT),
        'can_view_hr': has_role(user, HR_VIEW),
        'can_manage_hr': has_role(user, HR_MGMT),
        'can_edit_reporting': has_role(user, REPORTING_EDIT),
        'can_manage_integrations': has_role(user, INTEGRATION_MGMT),
    }
