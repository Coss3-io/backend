from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import MaxLengthValidator, MinLengthValidator
from api.models.types import Address


class MyUserManager(BaseUserManager):
    """The custom user manager for user creation"""

    def create_user(self, address: Address):
        """Method to create a regular user

        address -- 42 characters long string"""

        user = self.model(address=address)
        user.save(using=self._db)
        return user

    def create_superuser(self, address: Address):
        """Method to create a super user

        address -- 42 characters long string"""

        user = self.create_user(address)
        user.isAdmin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    address = models.CharField(
        null=False,
        blank=False,
        max_length=42,
        unique=True,
        validators=[
            MinLengthValidator(limit_value=42),
            MaxLengthValidator(limit_value=42),
        ],
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = "address"
