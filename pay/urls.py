from django.urls import path
from django.views.generic import TemplateView
from .views import PagamentoCheckView

urlpatterns = [
    path("pagamentos/", TemplateView.as_view(template_name="check_pagamentos.html"), name="home"),
    path("check-pagamentos/", PagamentoCheckView.as_view(), name="check_pagamentos"),
]
