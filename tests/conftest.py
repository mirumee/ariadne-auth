import dataclasses

import pytest

from ariadne_auth.authz import AuthorizationExtension
from ariadne_auth.types import PermissionsList


@dataclasses.dataclass
class PermissionObject:
    permissions: list[str]

    def has_permissions(self, permissions: list[str]) -> bool:
        return all(p in self.permissions for p in permissions)


def permission_object_factory(permissions: PermissionsList) -> PermissionObject:
    return PermissionObject(permissions=permissions)


@pytest.fixture
def no_permissions_object() -> PermissionObject:
    return permission_object_factory([])


@pytest.fixture
def read_comments_permissions_object() -> PermissionObject:
    return permission_object_factory(["read:Comments"])


@pytest.fixture
def test_authz() -> AuthorizationExtension:
    return AuthorizationExtension(
        permissions_object_provider_fn=lambda _: permission_object_factory([])
    )
