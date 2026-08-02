# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _

from modules.base.models.base import BaseModel


class Source(BaseModel):
    """Where a partner came from (referral, walk-in, website, agent, ad campaign, ...)."""

    name = models.CharField(_("Source Name"), max_length=100)
    description = models.CharField(
        _("Description"), max_length=255, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Partner Source")
        verbose_name_plural = _("Partner Sources")
        ordering = ["name"]

    def __str__(self):
        return self.name
