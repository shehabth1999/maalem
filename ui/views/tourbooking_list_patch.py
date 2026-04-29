# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _

tourbooking_list_maalem_patch = {
    "key": "tourbooking_list_maalem_patch",
    "name": "Tour Booking List - Maalem Export Action",
    "model": "tourism.tourbooking",
    "view_type": "list",
    "priority": 50,
    "inherit_mode": "extension",
    "inherit_id": "tourism_booking_list",
    "module": "tourism",
    "inheritance_operations": [
        {
            "operation": "append",
            "target": "header.actions",
            "content": [
                {
                    "name": "action_export_partners_excel",
                    "string": _("Export Partners (Excel)"),
                    "icon": "FileSpreadsheet",
                    "type": "server",
                    "as": "button",
                    "variant": "success",
                    "selection_required": True,
                    "confirm_required": False,
                }
            ],
        }
    ],
}
