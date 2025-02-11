from typing import Callable, Protocol, Union

from graphql import GraphQLResolveInfo
from typing_extensions import TypeAlias, TypeAliasType

Permission: TypeAlias = str
PermissionsList: TypeAlias = list[Permission]


class HasPermissions(Protocol):
    def has_permissions(self, permissions: PermissionsList) -> bool: ...


PermissionsResolver = TypeAliasType(
    "PermissionsResolver", Callable[[GraphQLResolveInfo], HasPermissions]
)

OptionalPermissionsResolver = TypeAliasType(
    "OptionalPermissionsResolver",
    Union[Callable[[GraphQLResolveInfo], HasPermissions], None],
)
