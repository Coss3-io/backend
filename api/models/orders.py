from django.db import models
from django.core.validators import MinLengthValidator


class Maker(models.Model):
    """The maker order class to store user orders into the database"""

    OPEN = "OP"
    CANCELLED = "CA"
    FILLED = "FI"
    STATUS_CHOICES = [(OPEN, "OPEN"), (CANCELLED, "CANCELLED"), (FILLED, "FILLED")]

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(filled__lte=models.F("amount")), name="filled_lte_amount"
            )
        ]

    owner = models.ForeignKey(
        "User", on_delete=models.CASCADE, editable=False, null=False, blank=False
    )
    bot = models.ForeignKey(
        "Bot", on_delete=models.CASCADE, editable=False, null=True, blank=True, related_name="orders"
    )
    base_token = models.CharField(
        null=False,
        blank=False,
        editable=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
        ],
    )
    quote_token = models.CharField(
        null=False,
        blank=False,
        editable=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
        ],
    )
    amount = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    filled = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    price = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    is_buyer = models.BooleanField(null=False, blank=False, editable=False)
    expiry = models.DateField(
        null=False,
        blank=False,
        editable=False,
    )
    status = models.CharField(
        max_length=2, choices=STATUS_CHOICES, default=OPEN, null=False, blank=False
    )
    hash = models.CharField(
        null=False,
        blank=False,
        editable=False,
        unique=True,
        max_length=66,
        validators=[
            MinLengthValidator(limit_value=66),
        ],
    )
    signature = models.CharField(
        null=False,
        blank=False,
        editable=False,
        max_length=132,
        validators=[
            MinLengthValidator(limit_value=132),
        ],
    )


class Taker(models.Model):
    """The Taker class for taker orders"""

    maker = models.ForeignKey(
        "Maker",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        editable=False,
    )
    taker = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        editable=False,
    )
    taker_amount = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    base_fees = models.BooleanField(
        null=False,
        blank=False,
        editable=False,
    )
    fees = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )


class Bot(models.Model):
    """The model used to store replace orders data, and group them to a"""

    step = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    maker_fees = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    upper_bound = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    lower_bound = models.DecimalField(
        max_digits=78,
        decimal_places=78,
        null=False,
        blank=False,
        editable=False,
    )
    fees_earned = models.DecimalField(
        max_digits=78,
        decimal_places=78,
    )
