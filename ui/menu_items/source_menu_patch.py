# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _


menu_dict = {
    "contacts_main_menu_features_source": {
        "name": _("Partner Sources"),
        "icon": "Compass",
        "module": "maalem",
        "model": "maalem.source",
        "sequence": 5,
        "parent_key": "contacts_main_menu_features",
        "allowed_groups": ["contacts.users"],
    }
}
