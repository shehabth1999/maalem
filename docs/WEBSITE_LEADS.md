# Website leads → auto-assigned to sellers + notification

**What it does.** Every ticket request the website (maalemtours.com, WordPress) sends to the
ERP becomes a CRM lead, exactly as before. The ERP now gives that lead a **seller** the
moment it is created and sends an **inbox + push notification** to the seller and to the
WhatsApp account admins. Clicking the notification opens the lead form.

Nothing changed on the website side. It keeps calling

```
POST https://maalem.genie-erp.com/api/v1/crm/lead/
Authorization: Token <admin token>
```

## How a website lead is recognised

All four must hold, otherwise the lead is left exactly as posted:

| Check | Value |
|---|---|
| Request path | `/api/v1/crm/lead/` (the generic model API) |
| `User-Agent` contains | `maalemtours.com` (WordPress sends `WordPress/7.1.x; https://maalemtours.com`) |
| Lead name starts with | `Reservation #` |
| `assigned_to` in the payload | empty |

## Who gets the lead

- **Pool**: the active *Users* of the WhatsApp account **"Maalem Tours" (id 1)**. Add or remove
  a seller on the account's form and the rotation follows immediately. Account *Admins* are not
  in the pool unless they are also in Users.
- **Rotation**: round-robin by user id. Next seller = the lowest user id greater than the last
  served id, wrapping to the lowest. Presence (online/offline) is ignored.
- **Same customer**: if the customer (same partner) already has an **open** lead with a seller,
  the new lead goes to that seller and the rotation does not move. This keeps the double
  submissions the site sometimes sends seconds apart with one seller.
- **Empty pool / account missing**: the lead is created without a seller and a warning is logged.
  The website's request never fails because of this feature.

## Notifications (Arabic)

| Recipient | Subject | Body |
|---|---|---|
| Seller, new customer | عميل جديد من الموقع | تم تعيين طلب جديد من الموقع لك: `<lead>` — `<customer>` — `<phone>` |
| Seller, returning customer | عميل جديد من الموقع | طلب جديد من عميلك `<customer>` على الموقع: `<lead>` |
| Account admins | تعيين عميل من الموقع | تم تعيين الطلب `<lead>` — `<customer>` إلى `<seller>` |

All carry the lead's form URL (`/genie/<menu>/?model=crm.lead&...&id=<lead id>`), category
`general` (always delivered, respects Do-Not-Disturb for push only).

## Settings → System Parameters (all optional)

| Key | Default | Meaning |
|---|---|---|
| `maalem.website_lead.whatsapp_account_id` | `1` | WhatsApp account whose Users are the pool |
| `maalem.website_lead.last_user_id` | created on first use | Rotation pointer. Set to `0` to restart from the lowest id |
| `maalem.website_lead.user_agent_marker` | `maalemtours.com` | Text that must appear in the request's User-Agent |
| `maalem.website_lead.name_prefix` | `Reservation #` | Lead name prefix the website uses |

## Backfill of older unassigned website leads

```
uv run python manage.py assign_website_leads --dry-run     # shows who would get what
uv run python manage.py assign_website_leads               # assigns + notifies
uv run python manage.py assign_website_leads --no-notify   # assigns silently
uv run python manage.py assign_website_leads --limit 10    # oldest 10 only
```

Open leads only by default (`--include-closed` to widen). Same rules as the live hook.

## Where the code lives

- `maalem/services/website_lead.py` — recognition, rotation, notifications.
- `maalem/extensions.py` → `LeadExtension` — `pre_create` sets `assigned_to` before the insert
  (so the sales team is filled by the lead's own `pre_save`); `post_create` notifies after commit.
- `maalem/management/commands/assign_website_leads.py` — backfill.
- `maalem/tests.py` — `FORCE_EXTENSIONS=true uv run python manage.py test maalem --keepdb`
  (the API-flow tests are skipped when the extension is not applied).

No schema change, no migration, no core change.
