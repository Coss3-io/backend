from decimal import Decimal
from django.contrib import admin
from django.conf import settings
from api.models.orders import Maker, Taker


def trim_zero(number):
    """Function used to show 18 decimal numbers as regular number"""
    number = Decimal(number) / Decimal("1e18")

    if number > Decimal("1") and number % Decimal("1") == Decimal("0"):
        return number.quantize(Decimal("1."))
    else:
        return number.quantize(Decimal("1e-3"))


def format_token(token):
    if token in settings.TOKENS:
        return settings.TOKENS[token]
    else:
        return token[0:9] + "..."


class TakerInlines(admin.TabularInline):
    model = Taker
    extra = 0


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
        return format_token(obj.base_token)

    @admin.display(description="Quote")
    def quote(self, obj: Maker):
        "infer the token symbol from the address"
        return format_token(obj.quote_token)

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
    list_select_related = ["user", "maker"]
    ordering = ["-date"]

    list_display = [
        "__str__",
        "date",
        "is_buyer",
        "amount_formatted",
        "price_formatted",
        "base",
        "quote",
        "base_fees",
        "fees_formatted",
        "block",
    ]

    readonly_fields = ["maker", "user", "date"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    ("maker", "user", "date"),
                    "taker_amount",
                    "fees",
                    ("base_fees", "is_buyer"),
                    "block",
                ],
                "classes": ["wide"]
            },
        ),
    ]

    @admin.display(description="Base")
    def base(self, obj: Taker):
        "infer the token symbol from the address"
        return format_token(obj.maker.base_token)

    @admin.display(description="Quote")
    def quote(self, obj: Taker):
        "infer the token symbol from the address"
        return format_token(obj.maker.quote_token)

    @admin.display(description="Amount")
    def amount_formatted(self, obj: Taker):
        return trim_zero(obj.taker_amount)

    @admin.display(description="Fees")
    def fees_formatted(self, obj: Taker):
        return (Decimal(obj.fees) / Decimal("1e18")).quantize(Decimal("1e-12"))

    @admin.display(description="Price")
    def price_formatted(self, obj: Taker):
        return trim_zero(obj.maker.price)
