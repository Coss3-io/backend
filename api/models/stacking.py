from decimal import Decimal
from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator


class Stacking(models.Model):
    """Model used to track the amount stacked by the users"""
    
    class Meta:
        constraints = [models.constraints.UniqueConstraint(fields=("user", "slot"), name="unique_user_and_slot")]

    amount = models.DecimalField(
        max_digits=78, decimal_places=0, null=False, blank=False, default=Decimal("0")
    )
    slot = models.IntegerField(null=False, blank=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False, blank=False)


class StackingFees(models.Model):
    """Model used to track the fees sent to the stacking contract"""

    class Meta:
        constraints = [models.constraints.UniqueConstraint(fields=("token", "slot"), name="unique_token_and_slot")]

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
