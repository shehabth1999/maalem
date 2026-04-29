# -*- coding: utf-8 -*-
from io import BytesIO
from modules.base.model_inheritance import ModelExtension
from modules.base.decorators import onchange, action
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
    date_of_birth = models.DateField(
        _("Date of Birth"), blank=True, null=True
    )
    passport_expiry_date = models.DateField(
        _("Passport Expiry Date"), blank=True, null=True
    )
    national_id = models.CharField(
        _("National ID / Civil ID"), max_length=50, blank=True, null=True
    )
    passport_number = models.CharField(
        _("Passport Number"), max_length=50, blank=True, null=True
    )
    age = models.IntegerField(_("Age"), blank=True, null=True)

    @onchange('date_of_birth')
    def _onchange_date_of_birth(self):
        from datetime import date as _date
        dob = self.date_of_birth
        if isinstance(dob, str) and dob:
            try:
                dob = _date.fromisoformat(dob[:10])
            except ValueError:
                self.age = None
                return
        if dob:
            today = timezone.now().date()
            self.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            self.age = None


EXPORT_HEADERS = ['passport_number', 'name', 'birth_date', 'phone', 'gender', 'national_id']


class TourBookingExtension(ModelExtension):
    """Maalem actions on tour bookings"""
    _inherit = 'tourism.tourbooking'
    _depends = ['tourism', 'maalem']

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
