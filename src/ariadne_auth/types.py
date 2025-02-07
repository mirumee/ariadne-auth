from typing import Protocol


type Permission = str
type PermissionsList = list[Permission]

class HasPermissions(Protocol):
    def has_permissions(self, permissions: PermissionsList) -> bool:
        ...

