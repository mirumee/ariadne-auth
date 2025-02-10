from typing import Any, Callable

from ariadne.types import ContextValue, Extension, Resolver
from graphql import GraphQLResolveInfo
from graphql.pyutils import is_awaitable

from ariadne_auth.exceptions import GraphQLErrorAuthorizationError
from ariadne_auth.types import HasPermissions, PermissionsList


class AuthorizationExtension(Extension):
    global_permissions: PermissionsList

    class PermissionChecker:
        def __init__(
            self, resolver: Resolver, permissions_policy_fn: Callable[..., Any]
        ) -> None:
            self.resolver = resolver
            self.permissions_policy_fn = permissions_policy_fn

        def __call__(self, obj, info: GraphQLResolveInfo, *args, **kwargs) -> Any:
            if not self.permissions_policy_fn(obj, info, *args, **kwargs):
                raise GraphQLErrorAuthorizationError()
            return self.resolver(obj, info, *args, **kwargs)

    def __init__(
        self, get_permission_obj: Callable[[GraphQLResolveInfo], HasPermissions]
    ) -> None:
        self.global_permissions: PermissionsList = []
        self.get_permission_obj = get_permission_obj

    def __call__(self, *args, **kwargs) -> "AuthorizationExtension":
        # make a new instance for each request to make it safe across requests
        # having one instance for all requests could cause a clumsy leak from
        # one request to another
        new = self.__class__(self.get_permission_obj)
        new.global_permissions = self.global_permissions

        return new

    def set_required_global_permissions(self, permissions: PermissionsList) -> None:
        self.global_permissions = permissions

    def permissions_policy_fn(self, permissions: PermissionsList) -> Callable[..., Any]:
        def inner(obj, info: GraphQLResolveInfo, *args, **kwargs) -> bool:
            perm_obj = self.get_permission_obj(info)
            return perm_obj.has_permissions(permissions)

        return inner

    def require_permissions(
        self,
        permissions: PermissionsList,
        ignore_global_permissions: bool = False,
    ) -> Resolver:
        def decorator(resolver: Resolver) -> Resolver:
            if not permissions and ignore_global_permissions:
                return resolver
            return self.PermissionChecker(
                resolver,
                self.permissions_policy_fn(
                    permissions
                    if ignore_global_permissions
                    else (permissions + self.global_permissions)
                ),
            )

        return decorator

    @staticmethod
    def assert_permissions(
        permission_object: HasPermissions, permissions: PermissionsList
    ) -> None:
        if not permission_object.has_permissions(permissions):
            raise GraphQLErrorAuthorizationError()

    def generate_authz_context(self, request: ContextValue):
        return {"auth": self}

    def resolve(
        self,
        next_: Resolver,
        obj: Any,
        info: GraphQLResolveInfo,
        *args,
        **kwargs,
    ):
        if not isinstance(next_, self.PermissionChecker) and self.global_permissions:
            next_ = self.PermissionChecker(
                next_, self.permissions_policy_fn(self.global_permissions)
            )

        if is_awaitable(next_):

            async def async_my_extension():
                result = await next_(obj, info, *args, **kwargs)
                if is_awaitable(result):
                    result = await result
                return result

            return async_my_extension()
        else:
            return next_(obj, info, *args, **kwargs)
