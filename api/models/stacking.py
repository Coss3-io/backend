from decimal import Decimal
from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator


class Stacking(models.Model):
    """Model used to track the amount stacked by the users"""

    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=("user", "slot"), name="unique_user_and_slot"
            )
        ]

    amount = models.DecimalField(
        max_digits=78, decimal_places=0, null=False, blank=False, default=Decimal("0")
    )
    slot = models.IntegerField(null=False, blank=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False, blank=False)
    chain_id = models.IntegerField(null=False, blank=False)

    def __str__(self):
        return f"User: {self.user.address}, Deposited {self.amount}, at {self.slot} block, on chain_id {self.chain_id}"


class StackingFeesWithdrawal(models.Model):
    """Model used to track the user FSA withdrawal from the contract"""

    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=("user", "slot", "token"),
                name="unique_withdrawal_per_user_token_slot",
            )
        ]

    slot = models.IntegerField(null=False, blank=False)
    token = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
            MaxLengthValidator(limit_value=42),
        ],
    )
    chain_id = models.IntegerField(null=False, blank=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return f"User: {self.user.address}, Withdrawn its {self.token}, at {self.slot} block, on chain_id {self.chain_id}"


class StackingFees(models.Model):
    """Model used to track the fees sent to the stacking contract"""

    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=("token", "slot"), name="unique_token_and_slot"
            )
        ]

    chain_id = models.IntegerField(null=False, blank=False)
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

    def __str__(self):
        return f"Fees received Token: {self.token}, Amount {self.amount}, at {self.slot} block, on chain_id {self.chain_id}"
