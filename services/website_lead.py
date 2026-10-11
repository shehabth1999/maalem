# -*- coding: utf-8 -*-
"""Website leads: auto-assign round-robin to the sellers and notify them.

The client's WordPress site (maalemtours.com) creates leads through the generic
model API, ``POST /api/v1/crm/lead/``, with the admin's token. Those leads used to
land with no owner and nobody was told. ``LeadExtension`` (maalem/extensions.py)
calls into this module from the lead's lifecycle hooks:

``pre_create``  → :func:`is_website_lead` + :func:`pick_seller`, sets ``assigned_to``
                  BEFORE the insert so ``Lead.pre_save`` fills the sales team;
``post_create`` → :func:`notify`, after the transaction committed.

Recognising a website lead (ALL must hold — anything else posted to the API is
left alone):
  * request path is the generic lead API (``/api/v1/crm/lead``);
  * ``User-Agent`` contains the site domain (WordPress sends
    ``WordPress/7.1.x; https://maalemtours.com`` on every call);
  * the lead name starts with the site's prefix (``Reservation #``);
  * no owner was posted.

Seller pool: the active ``users`` of the configured WhatsApp account (default 1).
Rotation: lowest user id strictly greater than the last served id, wrapping to the
lowest — the same stable id cycle as chat's distribution — with the pointer kept
in a system parameter and advanced under a row lock. A customer who already has
an open, owned lead keeps the same seller and the pointer does not move.

Configurable from Settings → System Parameters (see PARAM_* below; all optional):
  account id, rotation pointer, User-Agent marker, lead name prefix.
"""
import logging

from django.db import models, transaction

logger = logging.getLogger(__name__)

PARAM_ACCOUNT = 'maalem.website_lead.whatsapp_account_id'
PARAM_LAST_USER = 'maalem.website_lead.last_user_id'
PARAM_UA_MARKER = 'maalem.website_lead.user_agent_marker'
PARAM_NAME_PREFIX = 'maalem.website_lead.name_prefix'

DEFAULT_ACCOUNT_ID = 1
DEFAULT_UA_MARKER = 'maalemtours.com'
DEFAULT_NAME_PREFIX = 'Reservation #'

API_PATH_PREFIX = '/api/v1/crm/lead'

SUBJECT_SELLER = 'عميل جديد من الموقع'
BODY_NEW = 'تم تعيين طلب جديد من الموقع لك: %(lead)s — %(customer)s — %(phone)s'
BODY_SAME_CUSTOMER = 'طلب جديد من عميلك %(customer)s على الموقع: %(lead)s'
SUBJECT_ADMIN = 'تعيين عميل من الموقع'
BODY_ADMIN = 'تم تعيين الطلب %(lead)s — %(customer)s إلى %(seller)s'


# =============================================================================
# Recognition
# =============================================================================

def is_website_lead(lead, request=None):
    """True for a lead the website is creating right now (see module doc)."""
    if lead.assigned_to_id:
        return False
    request = request if request is not None else _current_request(lead)
    if request is None:
        return False
    if not (request.path or '').startswith(API_PATH_PREFIX):
        return False
    marker = _param(PARAM_UA_MARKER, DEFAULT_UA_MARKER).lower()
    if marker and marker not in (request.META.get('HTTP_USER_AGENT') or '').lower():
        return False
    return has_website_name(lead)


def has_website_name(lead):
    prefix = _param(PARAM_NAME_PREFIX, DEFAULT_NAME_PREFIX)
    return bool(prefix) and (lead.name or '').startswith(prefix)


def _current_request(lead):
    try:
        return lead.env.request
    except Exception:  # noqa: BLE001 — no request context (shell, worker)
        return None


# =============================================================================
# Seller selection
# =============================================================================

def pick_seller(lead):
    """(seller, same_customer). The owner of the customer's newest open lead when
    there is one, else the next seller in rotation. (None, False) when the
    account has no active users — the lead then stays unassigned."""
    owner = _current_owner_for(lead)
    if owner is not None:
        return owner, True
    account = get_account()
    if account is None:
        return None, False
    return next_seller(account), False


def _current_owner_for(lead):
    """Owner of the newest OPEN lead of the same customer, or None.

    ``all_objects``: the default manager is branch-aware and would hide leads
    outside the API user's branches. ``stage`` is nullable, so the NULL case is
    spelled out (as ``crm.models.lead.open_leads`` does).
    """
    from modules.crm.models import Lead

    qs = Lead.all_objects.filter(active=True, assigned_to__isnull=False).filter(
        models.Q(stage__isnull=True) | models.Q(stage__is_closed=False)
    )
    if lead.pk:
        qs = qs.exclude(pk=lead.pk)
    if lead.partner_id:
        qs = qs.filter(partner_id=lead.partner_id)
    elif lead.phone:
        qs = qs.filter(phone=lead.phone)
    else:
        return None
    match = qs.order_by('-created_at', '-id').select_related('assigned_to').first()
    if match is None or not match.assigned_to.is_active:
        return None
    return match.assigned_to


def get_account():
    """The WhatsApp account whose users are the seller pool, or None (logged)."""
    from modules.whatsapp.models import WhatsAppAccount

    raw = _param(PARAM_ACCOUNT, DEFAULT_ACCOUNT_ID)
    try:
        account_id = int(raw)
    except (TypeError, ValueError):
        account_id = DEFAULT_ACCOUNT_ID
    account = WhatsAppAccount.objects.filter(pk=account_id).first()
    if account is None:
        logger.warning('website lead: WhatsApp account %s not found (parameter %s)', account_id, PARAM_ACCOUNT)
    return account


def seller_pool(account):
    """Active users of the account in the id order the rotation walks."""
    return list(account.users.filter(is_active=True).order_by('id'))


def next_seller(account):
    """Advance the rotation and return the chosen user; None when the pool is empty."""
    from modules.base.models import ConfigParameter

    pool = seller_pool(account)
    if not pool:
        logger.warning('website lead: WhatsApp account %s has no active users', account.pk)
        return None

    with transaction.atomic():
        pointer = ConfigParameter.objects.select_for_update().filter(key=PARAM_LAST_USER).first()
        if pointer is None:
            ConfigParameter.objects.create(
                key=PARAM_LAST_USER, value='0',
                description='maalem: id of the last seller who received a website lead',
            )
            pointer = ConfigParameter.objects.select_for_update().get(key=PARAM_LAST_USER)
        try:
            last_id = int(pointer.value or 0)
        except ValueError:
            last_id = 0
        selected = next((u for u in pool if u.id > last_id), pool[0])
        pointer.value = str(selected.id)
        pointer.save(update_fields=['value', 'updated_at'])
    logger.debug('website lead: rotation %s -> %s', last_id, selected.id)
    return selected


# =============================================================================
# Notifications
# =============================================================================

def notify(lead, seller, same_customer=False):
    """Inbox + push to the seller, and to the account admins (minus the seller).
    Returns the lead URL. Never raises."""
    url = lead_url(lead)
    customer = (lead.partner.name if lead.partner_id else lead.contact_name) or lead.name
    ctx = {
        'lead': lead.name, 'customer': customer,
        'phone': lead.phone or lead.mobile or '-',
        'seller': _display(seller),
    }
    body = (BODY_SAME_CUSTOMER if same_customer else BODY_NEW) % ctx
    _post(seller.partner_id if seller else None, SUBJECT_SELLER, body, lead, url)

    account = get_account()
    if account is not None:
        admin_partner_ids = [
            pid for uid, pid in account.admins.filter(is_active=True).values_list('id', 'partner_id')
            if pid and (seller is None or uid != seller.id)
        ]
        if admin_partner_ids:
            _post(admin_partner_ids, SUBJECT_ADMIN, BODY_ADMIN % ctx, lead, url)
    return url


def lead_url(lead):
    try:
        from modules.base.models.menu_item import MenuItem
        return MenuItem.get_url_for_model(lead, view_type='form', id=lead.id)
    except Exception:  # noqa: BLE001
        logger.exception('website lead: could not build the URL of lead %s', lead.pk)
        return '/'


def _post(partner_ids, subject, body, lead, url):
    if not partner_ids:
        logger.warning('website lead: no partner to notify for lead %s (%s)', lead.pk, subject)
        return
    if isinstance(partner_ids, int):
        partner_ids = [partner_ids]
    try:
        from modules.notifications.services.post_notification import post_notification
        post_notification(
            partner_ids=partner_ids, body=body, subject=subject,
            record=lead, is_push=True, url=url, category='general',
        )
    except Exception:  # noqa: BLE001 — a failed notification must not fail the lead
        logger.exception('website lead: notification failed for lead %s', lead.pk)


def _display(user):
    if user is None:
        return '-'
    return getattr(user, 'name', None) or user.get_full_name() or user.username or str(user.pk)


def _param(key, default):
    from modules.base.models import ConfigParameter
    value = ConfigParameter.get_param(key, None)
    if value is None or str(value).strip() == '':
        return default
    return str(value).strip()
