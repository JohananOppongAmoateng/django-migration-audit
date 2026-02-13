from django.db import models


class E2EModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "test_e2e_app"
        db_table = "test_e2e_app_model"
