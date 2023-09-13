from decimal import Decimal
from django.contrib import admin
from django.conf import settings
from api.models import User
from api.models.orders import Bot, Maker, Taker
from api.models.stacking import Stacking, StackingFees


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
    show_change_link = True


class MakerInlines(admin.TabularInline):
    model = Maker
    extra = 0

    show_change_link = True
    fields = ["base_token", "quote_token", "amount", "price", "filled", "is_buyer"]
    readonly_fields = [
        "base_token",
        "quote_token",
        "amount",
        "price",
        "filled",
        "is_buyer",
    ]


class MakerListFilter(admin.SimpleListFilter):
    """List filter for maker base and quote tokens"""

    title = "Token Pair"
    parameter_name = "token_pair"


@admin.register(Maker)
class MakerAdmin(admin.ModelAdmin):
    inlines = [TakerInlines]
    ordering = ("expiry",)
    search_fields = ["base_token", "quote_token"]
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
        "bot",
        "user",
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
                    ("user", "bot"),
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
    search_fields = ["maker__base_token", "maker__quote_token"]
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
                "classes": ["wide"],
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


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    """Class used to manage the bots from the admin page"""

    inlines = [MakerInlines]
    ordering = ("date",)
    list_display = [
        "__str__",
        "date",
        "lower_bound_f",
        "upper_bound_f",
        "step_f",
        "price_f",
        "maker_fees_f",
        "fees_earned_f",
    ]

    readonly_fields = [
        "user",
        "date",
        "lower_bound",
        "upper_bound",
        "step",
        "price",
        "maker_fees",
        "fees_earned",
    ]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    (
                        "user",
                        "date",
                    )
                ],
                "classes": ["wide"],
            },
        ),
        (
            "Order Details",
            {
                "fields": [
                    ("lower_bound", "upper_bound"),
                    ("price", "step"),
                    ("fees_earned", "maker_fees"),
                ],
                "classes": ["wide"],
            },
        ),
    ]

    @admin.display(description="lower_bound")
    def lower_bound_f(self, obj: Bot):
        return trim_zero(obj.lower_bound)

    @admin.display(description="upper_bound")
    def upper_bound_f(self, obj: Bot):
        return trim_zero(obj.upper_bound)

    @admin.display(description="step")
    def step_f(self, obj: Bot):
        return trim_zero(obj.step)

    @admin.display(description="price")
    def price_f(self, obj: Bot):
        return trim_zero(obj.price)

    @admin.display(description="maker_fees")
    def maker_fees_f(self, obj: Bot):
        return trim_zero(obj.maker_fees)

    @admin.display(description="fees_earned")
    def fees_earned_f(self, obj: Bot):
        return trim_zero(obj.fees_earned)


@admin.register(Stacking)
class StackingAdmin(admin.ModelAdmin):
    """Admin interface user to interact with the stacking entries"""

    ordering = ("-slot",)
    search_fields = ["user__address"]
    list_display = ["user", "amount_f", "slot"]
    
    readonly_fields = ["user"]
    fields = ["user", ("amount", "slot")]

    @admin.display(description="amount")
    def amount_f(self, obj: Stacking):
        return trim_zero(obj.amount)

@admin.register(StackingFees)
class StackingFeesAdmin(admin.ModelAdmin):
    """Admin interface user to interact with the stackingfees entries"""

    ordering = ("-slot",)
    search_fields = ["token"]
    list_display = ["token_f", "amount_f", "slot"]
    
    readonly_fields = ["token"]
    fields = ["token", ("amount", "slot")]

    @admin.display(description="amount")
    def amount_f(self, obj: Stacking):
        return trim_zero(obj.amount)

    @admin.display(description="Token")
    def token_f(self, obj: StackingFees):
        "infer the token symbol from the address"
        return format_token(obj.token)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """User admin interface"""
    pass
