# -*- coding: utf-8 -*-
"""
Access rights for maalem module.
Format: [view, add, change, delete] as [0/1, 0/1, 0/1, 0/1]
"""

# Permission patterns for convenience
PERMISSION_PATTERNS = {
    'NONE': [0, 0, 0, 0],           # No access
    'VIEW_ONLY': [1, 0, 0, 0],      # View only
    'MANAGE': [1, 1, 1, 0],         # Manage but no delete
    'FULL': [1, 1, 1, 1],           # Full access
}

MODEL_PERMISSIONS = [
    {
        'model': 'maalem.source',
        'group': 'tourism.users',
        'permissions': PERMISSION_PATTERNS['MANAGE'],  # view, add, change, no delete
    },
]

# Example using patterns:
# {
#     'model': 'maalem.modelname',
#     'group': 'maalem.users',
#     'permissions': PERMISSION_PATTERNS['MANAGE'],
# }
