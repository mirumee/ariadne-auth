from typing import Protocol

from typing_extensions import TypeAlias

Permission: TypeAlias = str
PermissionsList: TypeAlias = list[Permission]


class HasPermissions(Protocol):
    def has_permissions(self, permissions: PermissionsList) -> bool: ...
