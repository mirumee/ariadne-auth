from collections.abc import Awaitable
from typing import Callable, Protocol, Union

from graphql import GraphQLResolveInfo
from typing_extensions import TypeAlias, TypeAliasType

Permission: TypeAlias = str
PermissionsList: TypeAlias = list[Permission]


class HasPermissions(Protocol):
    def has_permissions(self, permissions: PermissionsList) -> bool: ...


class AsyncHasPermissions(Protocol):
    async def has_permissions(
        self, permissions: PermissionsList
    ) -> Awaitable[bool]: ...


HasPermissionsObject = TypeAliasType(
    "HasPermissionsObject", Union[HasPermissions, AsyncHasPermissions]
)

PermissionsResolver = TypeAliasType(
    "PermissionsResolver", Callable[[GraphQLResolveInfo], HasPermissionsObject]
)

OptionalPermissionsResolver = TypeAliasType(
    "OptionalPermissionsResolver",
    Union[PermissionsResolver, None],
)
