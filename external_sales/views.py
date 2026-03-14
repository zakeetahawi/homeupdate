from django.views.generic import TemplateView

from .mixins import DecoratorDeptRequiredMixin


class ExternalSalesIndexView(DecoratorDeptRequiredMixin, TemplateView):
    """Landing page for External Sales department — redirects/shows available sub-departments"""

    template_name = "external_sales/index.html"
