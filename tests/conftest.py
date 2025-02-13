import dataclasses
from typing import Union

import pytest

from ariadne_auth.authz import AuthorizationExtension
from ariadne_auth.types import PermissionsList


@dataclasses.dataclass
class PermissionObject:
    permissions: list[str]

    def has_permissions(self, permissions: list[str]) -> bool:
        return all(p in self.permissions for p in permissions)


@dataclasses.dataclass
class AsyncPermissionObject:
    permissions: list[str]

    async def has_permissions(self, permissions: list[str]) -> bool:
        return all(p in self.permissions for p in permissions)


def permissions_object_factory(
    permissions: PermissionsList, async_has_permissions: bool = False
) -> Union[AsyncPermissionObject, PermissionObject]:
    perm_obj = AsyncPermissionObject if async_has_permissions else PermissionObject
    return perm_obj(permissions=permissions)


@pytest.fixture
def no_permissions_object() -> PermissionObject:
    return permissions_object_factory([], async_has_permissions=False)


@pytest.fixture
def read_comments_permissions_object() -> PermissionObject:
    return permissions_object_factory(["read:Comments"])


@pytest.fixture
def test_authz() -> AuthorizationExtension:
    return AuthorizationExtension(
        permissions_object_provider_fn=lambda _: permissions_object_factory(
            [], async_has_permissions=False
        )
    )
