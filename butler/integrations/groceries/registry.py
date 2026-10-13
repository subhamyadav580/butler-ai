"""The grocery apps Butler can compare. Adding one: a provider in providers/
and a line here."""

from .providers.instamart import InstamartProvider
from .providers.zepto import ZeptoProvider

PROVIDERS = [InstamartProvider(), ZeptoProvider()]


def available_providers():
    """Apps whose tools are loaded in the running agent."""
    return [p for p in PROVIDERS if p.available()]
