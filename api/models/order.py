from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator


class Maker(models.Model):
    """The maker order class to store user orders into the database"""

    # owner user
    base_token = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        validators=[
            MinLengthValidator(limit_value=42),
            MaxLengthValidator(limit_value=42),
        ],
    )
    quote_token = models.CharField(
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
    filled = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    is_buyer = models.BooleanField(null=False, blank=False)
    expiry = models.DateField(null=False, blank=False)
    # status CHOICE field
    # hash
    # signature unique

    # constraint


class AbstractTaker(models.Model):
    """The abstract Taker class for regular taker and replaceTaker"""

    class Meta:
        abstract = True

    taker_amount = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    base_fees = models.BooleanField(null=False, blank=False)
    fees = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )


class Taker(AbstractTaker):
    """The taker order model for regular maker orders"""

    maker = models.ForeignKey("Maker", on_delete=models.PROTECT)


class ReplaceTaker(AbstractTaker):
    """The class used to describe taker orders"""

    maker = models.ForeignKey("ReplaceMaker", on_delete=models.PROTECT)
    mult = models.BigIntegerField(null=False, blank=False)


class ReplaceMaker(Maker):
    """The class used to describe replace maker orders"""

    price = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    step = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    maker_fees = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    upper_bound = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
    lower_bound = models.DecimalField(
        max_digits=78, decimal_places=78, null=False, blank=False
    )
