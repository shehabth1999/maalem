# -*- coding: utf-8 -*-
from io import BytesIO
from modules.base.model_inheritance import ModelExtension
from modules.base.decorators import action
from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from openpyxl import Workbook


class PartnerExtension(ModelExtension):
    """Extend Partner with Maalem personal/identity fields"""
    _inherit = 'base.partner'
    _depends = ['base', 'maalem']

    additional_phone = models.CharField(
        _("Additional Phone"), max_length=20, blank=True, null=True
    )

    source = models.ForeignKey(
        'maalem.Source',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partners',
        verbose_name=_("Source"),
        help_text=_("Where this partner came from (referral, walk-in, website, agent, ad campaign, ...)"),
    )


EXPORT_HEADERS = ['passport_number', 'name', 'birth_date', 'phone', 'gender', 'national_id']


class TourBookingExtension(ModelExtension):
    """Maalem actions on tour bookings"""
    _inherit = 'tourism.tourbooking'
    _depends = ['tourism', 'maalem']

    # Informational only: lets the agent pick the bedding/occupancy type on the
    # booking header. Same catalog the hotel lines use, no pricing/logic impact.
    accommodation_type = models.ForeignKey(
        'tourism.AccommodationType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maalem_tour_bookings',
        verbose_name=_("Accommodation Type"),
    )

    @action
    def action_export_partners_excel(queryset):
        seen = set()
        partners = []
        for booking in queryset:
            partner = getattr(booking, 'partner', None)
            if not partner or partner.id in seen:
                continue
            seen.add(partner.id)
            partners.append(partner)

        if not partners:
            return {
                'status': False,
                'open_mode': 'message',
                'message': 'No partners found on the selected bookings.',
                'data': {},
            }

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'export'
        sheet.append(EXPORT_HEADERS)
        for partner in partners:
            dob = getattr(partner, 'date_of_birth', None)
            sheet.append([
                getattr(partner, 'passport_number', '') or '',
                partner.name or '',
                dob.isoformat() if dob else '',
                partner.phone or '',
                getattr(partner, 'gender', '') or '',
                getattr(partner, 'national_id', '') or '',
            ])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'partners_{timestamp}.xlsx'
        saved_path = default_storage.save(
            f'exports/maalem/{filename}',
            ContentFile(buffer.getvalue()),
        )
        url = default_storage.url(saved_path)

        return {
            'status': True,
            'open_mode': 'pdf',
            'message': f'Exported {len(partners)} partner(s)',
            'data': {'pdf_url': url, 'filename': filename},
        }







class ConversationExtension(ModelExtension):
    _inherit = 'chat.conversation'

    def advance_lead_on_first_summary(self):
        """Advance the partner's latest CRM lead from stage 1 → 2 on first summarization."""
        from modules.crm.models.lead import Lead
        partner = self.social_partner
        if not partner:
            return
        latest_lead = partner.leads.order_by('-created_at').first()
        if latest_lead and latest_lead.stage_id == 1:
            latest_lead.stage_id = 2
            latest_lead.save()