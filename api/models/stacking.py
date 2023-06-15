from decimal import Decimal
from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator


class Stacking(models.Model):
    """Model used to track the amount stacked by the users"""

    amount = models.DecimalField(
        max_digits=78, decimal_places=0, null=False, blank=False
    )
    slot = models.IntegerField(null=False, blank=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False, blank=False)


class StakingFees(models.Model):
    """Model used to track the fees sent to the stacking contract"""

    class Meta:
        constraints = [models.constraints.UniqueConstraint(fields=("token", "slot"))]

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
        max_digits=78, decimal_places=0, null=False, blank=False, default=Decimal(0)
    )
    slot = models.IntegerField(null=False, blank=False)
