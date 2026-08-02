# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _


source_list_view = {
    "key": "source_list_view",
    "name": "Partner Sources list",
    "model": "maalem.source",
    "view_type": "list",
    "menu_item": "contacts_main_menu_features_source",
    "priority": 20,
    "module": "contacts",
    "body": {
        "tree": {
            "fields": [
                {
                    "name": "id",
                    "widget": "number",
                    "string": _("ID"),
                    "help": True,
                    "visible": False,
                    "editor": False,
                    "width": 80,
                    "formatter": "number",
                },
                {
                    "name": "name",
                    "widget": "text",
                    "string": _("Source Name"),
                    "help": _("Name of the partner source"),
                    "visible": True,
                    "editor": True,
                    "width": 200,
                },
                {
                    "name": "description",
                    "widget": "text",
                    "string": _("Description"),
                    "help": _("Optional description"),
                    "visible": True,
                    "editor": True,
                    "width": 300,
                },
                {
                    "name": "active",
                    "widget": "boolean",
                    "string": _("Active"),
                    "help": _("Whether this source is active"),
                    "visible": True,
                    "editor": True,
                    "width": 100,
                },
                {
                    "name": "created_at",
                    "widget": "datetime",
                    "string": _("Created"),
                    "help": _("Creation date"),
                    "visible": True,
                    "editor": False,
                    "width": 160,
                },
            ]
        }
    },
}


source_form_view = {
    "key": "source_form_view",
    "name": "Partner Source",
    "model": "maalem.source",
    "view_type": "form",
    "menu_item": "contacts_main_menu_features_source",
    "priority": 20,
    "module": "contacts",
    "body": {
        "sheet": {
            "title": {
                "fields": [
                    {
                        "name": "name",
                        "string": _("Source Name"),
                        "widget": "text",
                        "required": True,
                        "readonly": False,
                        "placeholder": _("e.g. Walk-in, Referral, Website"),
                        "minLength": None,
                        "maxLength": 100,
                        "showLengthCounter": True,
                    }
                ]
            },
            "sections": [
                {
                    "title": "",
                    "groups": [
                        {
                            "title": "",
                            "fields": [
                                {
                                    "name": "description",
                                    "string": _("Description"),
                                    "widget": "textarea",
                                    "required": False,
                                    "readonly": False,
                                    "placeholder": _("Optional description"),
                                    "rows": 3,
                                    "minLength": None,
                                    "maxLength": 255,
                                    "showLengthCounter": True,
                                },
                                {
                                    "name": "active",
                                    "string": _("Active"),
                                    "widget": "switch",
                                    "required": False,
                                    "readonly": False,
                                    "switchLabel": None,
                                },
                            ],
                        }
                    ],
                }
            ],
            "tabs": [],
        }
    },
}
