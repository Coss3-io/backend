from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator


class Stacking(models.Model):
    """Model used to track the amount stacked by the users"""

    amount = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    slot = models.IntegerField(null=False, blank=False)
    # user


class StakingFees(models.Model):
    """Model used to track the fees sent to the stacking contract"""

    token = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
            MaxLengthValidator(limit_value=42),
        ],
    )
    amount = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    slot = models.IntegerField(null=False, blank=False)
