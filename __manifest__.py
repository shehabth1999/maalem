# -*- coding: utf-8 -*-
{
    'name': 'maalem',
    'technical_name': 'maalem',
    'type': 'app',
    'summary': 'this is the maalem module',
    'description': """
this is the maalem module
""",
    'author': "Genie ERP",
    'website': "https://www.aigeniecrm.com",
    'category': 'Maalem',
    'version': '0.0.1',
    # 'chat' + 'crm': ConversationExtension extends chat.conversation and reaches into
    # modules.crm.models.lead from advance_lead_on_first_summary.
    'depends': ['base', 'contacts', 'tourism', 'chat', 'crm'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
