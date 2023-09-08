from decimal import Decimal
from django.contrib import admin
from django.conf import settings
from api.models.orders import Maker, Taker


def trim_zero(number):
    """Function used to show 18 decimal numbers as regular number"""
    number = Decimal(number) / Decimal("1e18")

    if number > Decimal("1"):
        return number.quantize(Decimal("1."))
    else:
        return number.quantize(Decimal("1e-3"))

class TakerInlines(admin.TabularInline):
    model = Taker

@admin.register(Maker)
class MakerAdmin(admin.ModelAdmin):
    inlines = [TakerInlines]
    ordering = ("expiry",)
    list_display = [
        "__str__",
        "amount_formatted",
        "price_formatted",
        "filled_formatted",
        "base",
        "quote",
        "expiry",
        "is_buyer",
        "status",
    ]

    readonly_fields = [
        "amount",
        "price",
        "base_token",
        "quote_token",
        "is_buyer",
        "expiry",
        "order_hash",
        "signature",
    ]

    radio_fields = {"status": admin.HORIZONTAL}

    fieldsets = [
        (
            "Order Details",
            {
                "fields": [
                    ("amount", "price", "filled"),
                    ("base_token", "quote_token"),
                    ("expiry", "is_buyer"),
                    "status",
                ]
            },
        ),
        (
            "Signature Details",
            {
                "fields": [
                    "order_hash",
                    "signature",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Base")
    def base(self, obj: Maker):
        "infer the token symbol from the address"
        if obj.base_token in settings.TOKENS:
            return settings.TOKENS[obj.base_token]
        else:
            return obj.base_token

    @admin.display(description="Quote")
    def quote(self, obj: Maker):
        "infer the token symbol from the address"
        if obj.quote_token in settings.TOKENS:
            return settings.TOKENS[obj.quote_token]
        else:
            return obj.quote_token[0:9] + "..."

    @admin.display(description="Amount")
    def amount_formatted(self, obj: Maker):
        return trim_zero(obj.amount)

    @admin.display(description="Price")
    def price_formatted(self, obj: Maker):
        return trim_zero(obj.price)

    @admin.display(description="Filled")
    def filled_formatted(self, obj: Maker):
        return trim_zero(obj.filled)


@admin.register(Taker)
class TakerAdmin(admin.ModelAdmin):
    pass
