# -*- coding: utf-8 -*-
"""Website leads: recognition, rotation, same-customer rule, notifications.

Run: uv run python manage.py test maalem
"""
import unittest
from decimal import Decimal

from django.test import TestCase, RequestFactory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from maalem.services import website_lead
from modules.base.models import Branch, Company, ConfigParameter, Currency, Partner, User
from modules.crm.models import Lead
from modules.crm.models.lead import Stage
from modules.notifications.models import Notification
from modules.whatsapp.models import WhatsAppAccount

WP_UA = 'WordPress/7.1.3; https://maalemtours.com'
API = '/api/v1/crm/lead/'


def _user(email, name, superuser=False):
    user = User.objects.create_user(email=email, password='x', name=name,
                                    is_superuser=superuser, is_staff=superuser)
    partner = Partner.objects.create(name=name)
    user.partner = partner
    user.save()
    return user


class WebsiteLeadBase(TestCase):
    def setUp(self):
        self.branch = Branch.objects.first()
        if self.branch is None:
            currency = Currency.objects.first() or Currency.objects.create(
                name='Egyptian Pound', symbol='E£', code='EGP', decimal_places=2,
                active=True, base=True, rounding=Decimal('0.01'))
            company = Company.objects.create(name='Maalem Test Co', currency=currency)
            self.branch = company.branches.first() or Branch.objects.create(name='HQ', code='HQ', company=company)
        self.company = self.branch.company
        self.open_stage = Stage.objects.create(name='New', sequence=10, is_closed=False, company=self.company)
        self.closed_stage = Stage.objects.create(name='Won', sequence=90, is_closed=True, is_won=True, company=self.company)

        self.admin = _user('admin@maalem.test', 'Admin', superuser=True)
        self.account = WhatsAppAccount.objects.create(name='Maalem Tours', phone_number_id='maalem-test')
        self.sellers = [_user(f's{i}@maalem.test', f'Seller {i}') for i in range(3)]
        for s in self.sellers:
            self.account.users.add(s)
        self.account.admins.add(self.admin)
        ConfigParameter.set_param(website_lead.PARAM_ACCOUNT, str(self.account.pk))
        ConfigParameter.objects.filter(key=website_lead.PARAM_LAST_USER).delete()

    def _api(self):
        token, _ = Token.objects.get_or_create(user=self.admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}', HTTP_USER_AGENT=WP_UA)
        return client

    def _post(self, client, name, phone, partner=None, **extra):
        body = {'name': name, 'phone': phone, 'branch': self.branch.pk, 'stage': self.open_stage.pk}
        if partner is not None:
            body['partner'] = partner.pk
        body.update(extra)
        # post_create (the notification) runs on commit; TestCase never commits.
        with self.captureOnCommitCallbacks(execute=True):
            return client.post(API, body, format='json')


class RotationTests(WebsiteLeadBase):
    def test_cycles_by_id_and_wraps(self):
        ids = [website_lead.next_seller(self.account).pk for _ in range(4)]
        ordered = sorted(s.pk for s in self.sellers)
        self.assertEqual(ids, ordered + ordered[:1])
        self.assertEqual(ConfigParameter.get_param(website_lead.PARAM_LAST_USER), str(ordered[0]))

    def test_inactive_user_is_skipped(self):
        self.sellers[1].is_active = False
        self.sellers[1].save()
        ids = {website_lead.next_seller(self.account).pk for _ in range(4)}
        self.assertNotIn(self.sellers[1].pk, ids)

    def test_empty_pool_returns_none(self):
        self.account.users.clear()
        self.assertIsNone(website_lead.next_seller(self.account))


class RecognitionTests(WebsiteLeadBase):
    def _lead(self, name='Reservation #R-1 - العمرة'):
        return Lead(name=name, branch=self.branch)

    def _request(self, path=API, ua=WP_UA):
        return RequestFactory().post(path, HTTP_USER_AGENT=ua)

    def test_website_request_is_recognised(self):
        self.assertTrue(website_lead.is_website_lead(self._lead(), self._request()))

    def test_other_user_agent_is_ignored(self):
        self.assertFalse(website_lead.is_website_lead(self._lead(), self._request(ua='curl/8.0')))

    def test_other_name_is_ignored(self):
        self.assertFalse(website_lead.is_website_lead(self._lead('Walk-in'), self._request()))

    def test_other_path_is_ignored(self):
        self.assertFalse(website_lead.is_website_lead(self._lead(), self._request(path='/genie/create/1/')))

    def test_posted_owner_is_kept(self):
        lead = self._lead()
        lead.assigned_to = self.admin
        self.assertFalse(website_lead.is_website_lead(lead, self._request()))

    def test_no_request_is_ignored(self):
        self.assertFalse(website_lead.is_website_lead(self._lead(), None) or website_lead.is_website_lead(self._lead()))


def _extension_applied():
    """True when the maalem LeadExtension hooks are chained on Lead (FORCE_EXTENSIONS=true)."""
    return any(
        getattr(h, '__module__', '') == 'maalem.extensions'
        for h in getattr(Lead, '_lifecycle_hook_chains', {}).get('pre_create', [])
    )


@unittest.skipUnless(
    _extension_applied(),
    'maalem LeadExtension not applied (run with FORCE_EXTENSIONS=true against a schema-synced test DB)',
)
class ApiFlowTests(WebsiteLeadBase):
    def test_website_post_assigns_and_notifies(self):
        client = self._api()
        customer = Partner.objects.create(name='Mahy', phone='+201000000001')
        resp = self._post(client, 'Reservation #R-1622 - العمرة', '+201000000001', partner=customer)
        self.assertEqual(resp.status_code, 201, resp.content)

        lead = Lead.all_objects.get(pk=resp.data['id'])
        first = sorted(self.sellers, key=lambda u: u.pk)[0]
        self.assertEqual(lead.assigned_to_id, first.pk)

        url = website_lead.lead_url(lead)
        seller_notes = Notification.objects.filter(res_partner=first.partner, url=url)
        self.assertEqual(seller_notes.count(), 1)
        self.assertIn('تم تعيين طلب جديد', seller_notes.first().mail_message_id.body)
        admin_notes = Notification.objects.filter(res_partner=self.admin.partner, url=url)
        self.assertEqual(admin_notes.count(), 1)
        self.assertIn('Seller', admin_notes.first().mail_message_id.body)

    def test_same_customer_keeps_seller_and_pointer(self):
        client = self._api()
        customer = Partner.objects.create(name='Repeat', phone='+201000000002')
        r1 = self._post(client, 'Reservation #R-1624 - العمرة', '+201000000002', partner=customer)
        r2 = self._post(client, 'Reservation #R-1625 - العمرة', '+201000000002', partner=customer)
        l1, l2 = Lead.all_objects.get(pk=r1.data['id']), Lead.all_objects.get(pk=r2.data['id'])
        self.assertEqual(l1.assigned_to_id, l2.assigned_to_id)
        self.assertEqual(ConfigParameter.get_param(website_lead.PARAM_LAST_USER), str(l1.assigned_to_id))
        latest = Notification.objects.filter(res_partner=l2.assigned_to.partner).order_by('-id').first()
        self.assertIn('عميلك', latest.mail_message_id.body)
        self.assertIn(l2.name, latest.mail_message_id.body)

    def test_closed_lead_does_not_pin_the_customer(self):
        client = self._api()
        customer = Partner.objects.create(name='Old', phone='+201000000003')
        Lead.all_objects.create(name='Reservation #R-1 - x', partner=customer, branch=self.branch,
                                stage=self.closed_stage, assigned_to=self.sellers[2])
        resp = self._post(client, 'Reservation #R-2 - x', '+201000000003', partner=customer)
        self.assertEqual(Lead.all_objects.get(pk=resp.data['id']).assigned_to_id,
                         sorted(self.sellers, key=lambda u: u.pk)[0].pk)

    def test_distinct_customers_rotate(self):
        client = self._api()
        assigned = []
        for i in range(4):
            p = Partner.objects.create(name=f'C{i}', phone=f'+2010000001{i:02d}')
            resp = self._post(client, f'Reservation #R-{i} - x', p.phone, partner=p)
            assigned.append(Lead.all_objects.get(pk=resp.data['id']).assigned_to_id)
        ordered = sorted(s.pk for s in self.sellers)
        self.assertEqual(assigned, ordered + ordered[:1])

    def test_non_website_api_post_is_untouched(self):
        client = self._api()
        resp = self._post(client, 'Walk-in customer', '+201000000004')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIsNone(Lead.all_objects.get(pk=resp.data['id']).assigned_to_id)
        client.credentials(HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'], HTTP_USER_AGENT='curl/8')
        resp = self._post(client, 'Reservation #R-9 - x', '+201000000005')
        self.assertIsNone(Lead.all_objects.get(pk=resp.data['id']).assigned_to_id)

    def test_empty_pool_still_creates_the_lead(self):
        self.account.users.clear()
        resp = self._post(self._api(), 'Reservation #R-7 - x', '+201000000006')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIsNone(Lead.all_objects.get(pk=resp.data['id']).assigned_to_id)
        self.assertFalse(Notification.objects.filter(res_partner=self.admin.partner).exists())

