# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _

partner_form_maalem_patch = {
    "key": "partner_form_maalem_patch",
    "name": "Partner Form - Maalem Personal Info",
    "model": "base.partner",
    "view_type": "form",
    "priority": 50,
    "inherit_mode": "extension",
    "inherit_id": "base_partner_form_view",
    "module": "contacts",
    "inheritance_operations": [
        {
            "operation": "prepend",
            "target": "sheet.tabs",
            "content": [
                {
                    "title": _("Personal Info"),
                    "sections": [
                        {
                            "title": _("Demographics"),
                            "groups": [
                                {
                                    "fields": [
                                        {
                                            "name": "gender",
                                            "string": _("gender"),
                                            "widget": "select",
                                            "required": False,
                                            "readonly": False,
                                            "help": _("The gender associated with this partner"),
                                            "options": {
                                                "male": _("Male"),
                                                "female": _("Female"),
                                                "unknown": _("Unknown"),
                                            },
                                            "defaultValue": "unknown",
                                        },
                                        {
                                            "name": "date_of_birth",
                                            "string": _("Date of Birth"),
                                            "widget": "date",
                                            "required": False,
                                            "onChange": True,
                                        },
                                        {
                                            "name": "age",
                                            "string": _("Age"),
                                            "widget": "number",
                                            "readonly": True,
                                        },
                                        {
                                            "name": "additional_phone",
                                            "string": _("Additional Phone"),
                                            "widget": "phone",
                                            "required": False,
                                        },
                                    ]
                                },
                                {
                                    "fields": [
                                        {
                                            "name": "national_id",
                                            "string": _("National ID / Civil ID"),
                                            "widget": "text",
                                            "required": False,
                                            "placeholder": _("Enter national or civil ID"),
                                        },
                                        {
                                            "name": "passport_number",
                                            "string": _("Passport Number"),
                                            "widget": "text",
                                            "required": False,
                                            "placeholder": _("Enter passport number"),
                                        },
                                        {
                                            "name": "passport_expiry_date",
                                            "string": _("Passport Expiry Date"),
                                            "widget": "date",
                                            "required": False,
                                        },
                                        {
                                            "name": "source",
                                            "string": _("Source"),
                                            "widget": "relation",
                                            "required": False,
                                            "placeholder": _("How did this contact reach us?"),
                                            "multiSelect": False,
                                            "creatable": True,
                                        },
                                    ]
                                }
                            ]
                        },
                    ]
                }
            ]
        }
    ]
}
