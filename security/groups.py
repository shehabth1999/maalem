# -*- coding: utf-8 -*-
"""
Security groups for maalem module

This file defines all security groups for the maalem module.
Groups are synced to the database using the sync_groups management command.
"""

GROUPS = [
    {
        'name': 'Maalem Users',
        'technical_name': 'maalem.users',
        'category': 'Maalem',
        'description': 'Access maalem module',
    },
    {
        'name': 'Maalem Admins',
        'technical_name': 'maalem.admins',
        'category': 'Maalem',
        'implied_groups': ['maalem.users'],
        'description': 'Manage all maalem module',
    }
]
