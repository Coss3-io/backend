from decimal import Decimal
from django.db import models
from django.core.validators import MinLengthValidator


class AsyncManager(models.Manager):
    async def create(self, *args, **kwargs):
        return await self.acreate(*args, **kwargs)


class Maker(models.Model):
    """The maker order class to store user orders into the database"""

    OPEN = "OP"
    CANCELLED = "CA"
    FILLED = "FI"
    STATUS_CHOICES = [(OPEN, "OPEN"), (CANCELLED, "CANCELLED"), (FILLED, "FILLED")]

    objects = AsyncManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(filled__lte=models.F("amount")), name="filled_lte_amount"
            ),
            models.CheckConstraint(
                check=~models.Q(base_token=models.F("quote_token")),
                name="base_token_difference_quote_token",
            ),
            models.CheckConstraint(
                check=models.Q(bot__isnull=False) | models.Q(user__isnull=False),
                name="bot_or_user_must_be_set",
            ),
        ]

    user = models.ForeignKey("User", on_delete=models.CASCADE, null=True, blank=True)
    bot = models.ForeignKey(
        "Bot", on_delete=models.CASCADE, null=True, blank=True, related_name="orders"
    )
    base_token = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
        ],
    )
    quote_token = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
        ],
    )
    amount = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    filled = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        default=Decimal("0"),
        null=False,
        blank=False,
    )
    price = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    is_buyer = models.BooleanField(null=False, blank=False)
    expiry = models.DateTimeField(
        null=False,
        blank=False,
    )
    status = models.CharField(
        max_length=2, choices=STATUS_CHOICES, default=OPEN, null=False, blank=False
    )
    order_hash = models.CharField(
        null=False,
        blank=False,
        unique=True,
        max_length=66,
        validators=[
            MinLengthValidator(limit_value=66),
        ],
    )
    signature = models.CharField(
        null=False,
        blank=False,
        max_length=132,
        validators=[
            MinLengthValidator(limit_value=132),
        ],
    )


class Taker(models.Model):
    """The Taker class for taker orders"""

    objects = AsyncManager()

    maker = models.ForeignKey(
        "Maker",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    block = models.BigIntegerField(null=False, blank=False)
    taker_amount = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    base_fees = models.BooleanField(
        null=False,
        blank=False,
    )
    fees = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    is_buyer = models.BooleanField(null=False, blank=False)


class Bot(models.Model):
    """The model used to store replace orders data, and group them to a"""

    user = models.ForeignKey("User", on_delete=models.CASCADE, null=False, blank=False)

    step = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    price = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    maker_fees = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    upper_bound = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    lower_bound = models.DecimalField(
        max_digits=78,
        decimal_places=0,
        null=False,
        blank=False,
    )
    fees_earned = models.DecimalField(
        max_digits=78, decimal_places=0, default=Decimal("0")
    )
