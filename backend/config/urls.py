"""Rutas raíz del proyecto: la API vive bajo /api/v1/."""

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("chibchaweb.web.urls")),
]
