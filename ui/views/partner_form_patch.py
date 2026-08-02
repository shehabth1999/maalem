# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _

partner_form_maalem_patch = {
    "key": "partner_form_maalem_patch",
    "name": "Partner Form - Maalem Fields",
    "model": "base.partner",
    "view_type": "form",
    "priority": 50,
    "inherit_mode": "extension",
    "inherit_id": "base_partner_form_view",
    "module": "contacts",
    "inheritance_operations": [
        {
            "operation": "after",
            "target": "field[name=mobile]",
            "content": {
                "name": "additional_phone",
                "string": _("Additional Phone"),
                "widget": "phone",
                "required": False,
                "placeholder": _("Enter additional phone number"),
            },
        },
        {
            "operation": "after",
            "target": "field[name=additional_phone]",
            "content": {
                "name": "source",
                "string": _("Source"),
                "widget": "relation",
                "required": False,
                "placeholder": _("How did this contact reach us?"),
                "multiSelect": False,
                "creatable": True,
            },
        },
    ],
}
