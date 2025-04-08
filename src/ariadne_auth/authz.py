from collections.abc import Coroutine
from inspect import iscoroutinefunction
from typing import Any, Callable

from ariadne.types import ContextValue, Extension, Resolver
from graphql import GraphQLResolveInfo
from graphql.pyutils import is_awaitable

from ariadne_auth.exceptions import GraphQLErrorAuthorizationError
from ariadne_auth.types import (
    AsyncHasPermissions,
    HasPermissions,
    OptionalPermissionsResolver,
    PermissionsList,
    PermissionsResolver,
)


class AuthorizationExtension(Extension):
    global_permissions: PermissionsList

    class PermissionChecker:
        def __init__(
            self, resolver: Resolver, permissions_policy_fn: Callable[..., Any]
        ) -> None:
            self.resolver = resolver
            self.permissions_policy_fn = permissions_policy_fn

        async def __call__(
            self, obj: Any, info: GraphQLResolveInfo, *args: Any, **kwargs: Any
        ) -> Any:
            has_permissions = self.permissions_policy_fn(obj, info, *args, **kwargs)

            if is_awaitable(has_permissions):
                has_permissions = await has_permissions

            if not has_permissions:
                raise GraphQLErrorAuthorizationError()

            result = self.resolver(obj, info, *args, **kwargs)
            if is_awaitable(result):
                return await result
            return result

    def __init__(self, permissions_object_provider_fn: PermissionsResolver) -> None:
        self.global_permissions: PermissionsList = []
        self.permissions_object_provider_fn = permissions_object_provider_fn

    def __call__(self, *args: Any, **kwargs: Any) -> "AuthorizationExtension":
        # make a new instance for each request to make it safe across requests
        # having one instance for all requests could cause a clumsy leak from
        # one request to another
        new = self.__class__(self.permissions_object_provider_fn)
        new.global_permissions = self.global_permissions

        return new

    def set_required_global_permissions(self, permissions: PermissionsList) -> None:
        self.global_permissions = permissions

    def permissions_policy_fn(
        self,
        permissions: PermissionsList,
        permissions_object_provider_fn: PermissionsResolver,
    ) -> Callable[..., Coroutine[Any, Any, bool]]:
        async def inner(
            obj: Any, info: GraphQLResolveInfo, *args: Any, **kwargs: Any
        ) -> bool:
            if iscoroutinefunction(permissions_object_provider_fn):
                perm_obj = await permissions_object_provider_fn(info)
            else:
                perm_obj = permissions_object_provider_fn(info)
            if iscoroutinefunction(perm_obj.has_permissions):
                return await perm_obj.has_permissions(permissions)  # type: ignore[no-any-return]
            return perm_obj.has_permissions(permissions)  # type: ignore[no-any-return]

        return inner

    def require_permissions(
        self,
        permissions: PermissionsList,
        ignore_global_permissions: bool = False,
        permissions_object_provider_fn: OptionalPermissionsResolver = None,
    ) -> Resolver:
        def decorator(resolver: Resolver) -> Resolver:
            if not permissions and ignore_global_permissions:
                return self.PermissionChecker(
                    resolver,
                    lambda *args, **kwargs: True,
                )

            # Append global permissions if ignore_global_permissions is False
            _permissions = (
                permissions
                if ignore_global_permissions
                else (permissions + self.global_permissions)
            )

            # Check if permissions_object_provider_fn is provided,
            # if not use the default one
            _permissions_object_provider_fn = (
                permissions_object_provider_fn or self.permissions_object_provider_fn
            )
            return self.PermissionChecker(
                resolver,
                self.permissions_policy_fn(
                    _permissions,
                    _permissions_object_provider_fn,
                ),
            )

        return decorator

    @staticmethod
    def assert_permissions(
        permission_object: HasPermissions, permissions: PermissionsList
    ) -> None:
        if not permission_object.has_permissions(permissions):
            raise GraphQLErrorAuthorizationError()

    @staticmethod
    async def assert_permissions_async(
        permission_object: AsyncHasPermissions, permissions: PermissionsList
    ) -> None:
        if not await permission_object.has_permissions(permissions):
            raise GraphQLErrorAuthorizationError()

    def generate_authz_context(
        self, request: ContextValue
    ) -> dict[str, "AuthorizationExtension"]:
        return {"auth": self}

    def resolve(
        self,
        next_: Resolver,
        obj: Any,
        info: GraphQLResolveInfo,
        **kwargs: Any,
    ) -> Any:
        try:
            resolver = info.parent_type.fields[info.field_name].resolve
        except (AttributeError, KeyError):
            resolver = next_
        if not isinstance(resolver, self.PermissionChecker) and self.global_permissions:
            next_ = self.PermissionChecker(
                next_,
                self.permissions_policy_fn(
                    self.global_permissions, self.permissions_object_provider_fn
                ),
            )

        if not iscoroutinefunction(next_):
            return next_(obj, info, **kwargs)

        async def async_my_extension() -> Any:
            result = await next_(obj, info, **kwargs)
            if is_awaitable(result):
                result = await result
            return result

        return async_my_extension()
