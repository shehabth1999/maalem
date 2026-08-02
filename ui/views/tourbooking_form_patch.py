# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _

tourbooking_form_maalem_patch = {
    "key": "tourbooking_form_maalem_patch",
    "name": "Tour Booking Form - Maalem Accommodation Type",
    "model": "tourism.tourbooking",
    "view_type": "form",
    "priority": 50,
    "inherit_mode": "extension",
    "inherit_id": "tourism_booking_form",
    "module": "tourism",
    "inheritance_operations": [
        {
            "operation": "after",
            "target": "field[name=package]",
            "content": {
                "name": "accommodation_type",
                "widget": "relation",
                "string": _("Accommodation Type"),
                "required": False,
                "multiSelect": False,
            },
        }
    ],
}
