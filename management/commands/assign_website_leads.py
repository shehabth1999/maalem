# -*- coding: utf-8 -*-
"""One-off backfill: give the website leads created before the auto-assignment
shipped a seller, and notify. Same rules as the live hook
(maalem/services/website_lead.py): same-customer first, else round-robin over
the configured WhatsApp account's users; seller + account admins notified.

    uv run python manage.py assign_website_leads --dry-run
    uv run python manage.py assign_website_leads
    uv run python manage.py assign_website_leads --no-notify --limit 10
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Assign unowned website leads (name prefix "Reservation #") to sellers round-robin and notify.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show the plan, write nothing.')
        parser.add_argument('--no-notify', action='store_true', help='Assign silently.')
        parser.add_argument('--limit', type=int, default=0, help='Process at most N leads (oldest first).')
        parser.add_argument('--include-closed', action='store_true',
                            help='Also assign leads in a closed stage (default: open leads only).')

    def handle(self, *args, **opts):
        from django.db.models import Q
        from maalem.services import website_lead
        from modules.crm.models import Lead
        from modules.crm.models.lead import resolve_team_for_user

        prefix = website_lead._param(website_lead.PARAM_NAME_PREFIX, website_lead.DEFAULT_NAME_PREFIX)
        account = website_lead.get_account()
        if account is None:
            self.stderr.write(self.style.ERROR('No WhatsApp account configured; nothing done.'))
            return
        pool = website_lead.seller_pool(account)
        self.stdout.write(f'Account: {account.name} (id {account.pk}); pool: '
                          + ', '.join(f'{u.pk}:{website_lead._display(u)}' for u in pool))
        if not pool:
            self.stderr.write(self.style.ERROR('The account has no active users; nothing done.'))
            return

        qs = Lead.all_objects.filter(active=True, assigned_to__isnull=True, name__startswith=prefix)
        if not opts['include_closed']:
            qs = qs.filter(Q(stage__isnull=True) | Q(stage__is_closed=False))
        qs = qs.order_by('created_at', 'id')
        if opts['limit']:
            qs = qs[:opts['limit']]
        leads = list(qs.select_related('partner'))
        self.stdout.write(f'{len(leads)} unassigned website lead(s) to process'
                          + (' (dry run)' if opts['dry_run'] else ''))

        if opts['dry_run']:
            # Simulate the rotation without touching the pointer.
            from modules.base.models import ConfigParameter
            try:
                last_id = int(ConfigParameter.get_param(website_lead.PARAM_LAST_USER, 0) or 0)
            except ValueError:
                last_id = 0
            simulated = {}  # partner_id -> seller, to mirror the same-customer rule
            for lead in leads:
                owner = website_lead._current_owner_for(lead) or simulated.get(lead.partner_id)
                if owner is not None:
                    seller, how = owner, 'same customer'
                else:
                    seller = next((u for u in pool if u.id > last_id), pool[0])
                    last_id = seller.id
                    how = 'rotation'
                if lead.partner_id:
                    simulated[lead.partner_id] = seller
                self.stdout.write(f'  lead {lead.pk} {lead.name!r} -> {website_lead._display(seller)} ({how})')
            return

        done = 0
        for lead in leads:
            with transaction.atomic():
                seller, same_customer = website_lead.pick_seller(lead)
                if seller is None:
                    self.stderr.write(f'  lead {lead.pk}: no seller available, skipped')
                    continue
                vals = {'assigned_to': seller, 'updated_at': timezone.now()}
                team = resolve_team_for_user(seller)
                if team:
                    vals['team'] = team
                # .update(): a one-column ownership change must not re-run the lead
                # hooks (same reasoning as crm.services.lead_assignment).
                Lead.all_objects.filter(pk=lead.pk).update(**vals)
                lead.assigned_to = seller
            if not opts['no_notify']:
                website_lead.notify(lead, seller, same_customer=same_customer)
            done += 1
            self.stdout.write(f'  lead {lead.pk} {lead.name!r} -> {website_lead._display(seller)}'
                              + (' (same customer)' if same_customer else ''))
        self.stdout.write(self.style.SUCCESS(f'Assigned {done} lead(s).'))
