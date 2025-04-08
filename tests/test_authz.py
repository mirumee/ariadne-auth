from unittest import mock

import pytest
from pytest_mock import MockerFixture

from ariadne_auth.authz import AuthorizationExtension
from ariadne_auth.exceptions import GraphQLErrorAuthorizationError
from tests.conftest import permissions_object_factory


def resolver(obj, info, *args, **kwargs):
    return "Hello, World!"


async def async_resolver(obj, info, *args, **kwargs):
    return "Hello, World! From async resolver"


def test_return_new_instance_on_every_authz_call(mocker: MockerFixture):
    permissions = ["read:Comments", "create:Ships"]
    permissions_object_provider_fn = mocker.Mock()

    authz = AuthorizationExtension(permissions_object_provider_fn)
    authz.set_required_global_permissions(permissions)

    new_authz = authz()
    another_authz = authz()

    assert new_authz is not authz
    assert new_authz.global_permissions == permissions

    assert another_authz is not authz
    assert another_authz.global_permissions == permissions

    assert another_authz is not new_authz


def test_set_required_global_permissions(test_authz: AuthorizationExtension):
    assert test_authz.global_permissions == []
    test_authz.set_required_global_permissions(["read:Comments", "create:Ships"])
    assert test_authz.global_permissions == ["read:Comments", "create:Ships"]


def test_assert_permissions(test_authz: AuthorizationExtension, no_permissions_object):
    assert test_authz.assert_permissions(no_permissions_object, []) is None

    with pytest.raises(GraphQLErrorAuthorizationError) as error:
        test_authz.assert_permissions(no_permissions_object, ["read:Comments"])

    assert error.value.message == "Permission denied"
    assert error.value.extensions == {"Authorization": {"errorType": "UNAUTHORIZED"}}


@pytest.mark.asyncio
async def test_assert_permissions_async(test_authz: AuthorizationExtension):
    async_permission_object = permissions_object_factory([], async_has_permissions=True)
    assert (
        await test_authz.assert_permissions_async(async_permission_object, []) is None
    )

    with pytest.raises(GraphQLErrorAuthorizationError) as error:
        await test_authz.assert_permissions_async(
            async_permission_object, ["read:Comments"]
        )

    assert error.value.message == "Permission denied"
    assert error.value.extensions == {"Authorization": {"errorType": "UNAUTHORIZED"}}


@pytest.mark.asyncio
async def test_require_permissions_no_permissions_async(
    test_authz: AuthorizationExtension,
):
    """No permission required, global permissions aren't set"""
    decorated_resolver = test_authz.require_permissions([])(resolver)
    assert await decorated_resolver(None, None) == "Hello, World!"


@pytest.mark.asyncio
async def test_require_permissions_no_permissions_global_permissions_disabled(
    test_authz: AuthorizationExtension,
):
    """Permissions are set, global permissions is set but disabled"""
    test_authz.set_required_global_permissions(["create:Comments"])
    decorated_resolver = test_authz.require_permissions(
        [], ignore_global_permissions=True
    )(resolver)
    assert await test_authz.resolve(decorated_resolver, None, None) == "Hello, World!"


@pytest.mark.asyncio
async def test_require_permissions_only_global_permissions(
    test_authz: AuthorizationExtension,
):
    """No permission required, global permissions is set"""
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions([])(resolver)

    with pytest.raises(GraphQLErrorAuthorizationError):
        assert await decorated_resolver(None, None)


@pytest.mark.asyncio
async def test_require_permissions_single_permission_no_global_permissions(
    test_authz: AuthorizationExtension,
):
    """Permissions are set, global permissions aren't set"""
    decorated_resolver = test_authz.require_permissions(
        ["read:Comments"], ignore_global_permissions=False
    )(resolver)
    with pytest.raises(GraphQLErrorAuthorizationError):
        assert await decorated_resolver(None, None)


@pytest.mark.asyncio
async def test_require_permissions_single_permission_global_permissions_disabled(
    test_authz: AuthorizationExtension,
):
    """Permissions are set, global permissions is set but disabled"""
    test_authz.set_required_global_permissions(["create:Comments"])
    decorated_resolver = test_authz.require_permissions(
        ["read:Comments"], ignore_global_permissions=True
    )(resolver)
    with pytest.raises(GraphQLErrorAuthorizationError):
        assert await decorated_resolver(None, None)


@pytest.mark.asyncio
async def test_require_permissions_global_permission_user_has_permissions(
    test_authz: AuthorizationExtension, read_comments_permissions_object
):
    """Global permission is set, user has the permission"""
    test_authz.permissions_object_provider_fn = (
        lambda _: read_comments_permissions_object
    )
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(
        [], ignore_global_permissions=False
    )(resolver)

    assert await decorated_resolver(None, None) == "Hello, World!"


@pytest.mark.asyncio
async def test_require_permission_with_async_object_provider(
    test_authz: AuthorizationExtension, read_comments_permissions_object
):
    async def permissions_object_provider_fn(info):
        return read_comments_permissions_object

    """Global permission is set, user has the permission"""
    test_authz.permissions_object_provider_fn = permissions_object_provider_fn
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(
        [], ignore_global_permissions=False
    )(resolver)

    assert await decorated_resolver(None, None) == "Hello, World!"


@pytest.mark.asyncio
async def test_require_permissions_set_permissions_and_global_fail(
    test_authz: AuthorizationExtension, read_comments_permissions_object
):
    """
    additional permissions are set,
    global permission is set, user only global permissions
    """
    test_authz.permissions_object_provider_fn = (
        lambda _: read_comments_permissions_object
    )
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(
        ["create:Comments"], ignore_global_permissions=False
    )(resolver)

    with pytest.raises(GraphQLErrorAuthorizationError):
        assert await decorated_resolver(None, None)


@pytest.mark.asyncio
async def test_require_permissions_set_permissions_and_global_pass(
    test_authz: AuthorizationExtension, read_comments_permissions_object
):
    """
    additional permissions are set,
    global permission is set, user has both permissions
    """
    read_comments_permissions_object.permissions.append("create:Comments")
    test_authz.permissions_object_provider_fn = (
        lambda _: read_comments_permissions_object
    )
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(
        ["create:Comments"], ignore_global_permissions=False
    )(resolver)

    assert await decorated_resolver(None, None)


def test_generate_authz_context(test_authz: AuthorizationExtension):
    context = test_authz.generate_authz_context(None)
    assert context == {"auth": test_authz}


def test_resolve_no_global_permissions_no_decorated(test_authz: AuthorizationExtension):
    assert test_authz.resolve(resolver, None, None) == "Hello, World!"


@pytest.mark.asyncio
async def test_resolve_global_permissions_default_resolver(
    test_authz: AuthorizationExtension,
):
    test_authz.set_required_global_permissions(["read:Comments"])

    with pytest.raises(GraphQLErrorAuthorizationError):
        assert await test_authz.resolve(resolver, None, None)


@pytest.mark.asyncio
async def test_resolve_async_resolver(test_authz: AuthorizationExtension):
    assert (
        await test_authz.resolve(async_resolver, None, None)
        == "Hello, World! From async resolver"
    )


@pytest.mark.asyncio
async def test_wrapped_extension(test_authz: AuthorizationExtension):
    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(
        [], ignore_global_permissions=True
    )(resolver)

    async def next_extension(*args, **kwargs):
        return decorated_resolver(*args, **kwargs)

    with pytest.raises(GraphQLErrorAuthorizationError):
        await test_authz.resolve(next_extension, None, None)

    mocked_info = mock.Mock(
        parent_type=mock.Mock(fields={"field": mock.Mock(resolve=decorated_resolver)}),
        field_name="field",
    )
    assert (
        await test_authz.resolve(next_extension, None, mocked_info) == "Hello, World!"
    )


@pytest.mark.asyncio
async def test_wrapped_resolver(test_authz: AuthorizationExtension):
    permission_object = permissions_object_factory(["read:Comments", "read:Posts"])
    test_authz.permissions_object_provider_fn = lambda _: permission_object

    test_authz.set_required_global_permissions(["read:Comments"])
    decorated_resolver = test_authz.require_permissions(["read:Posts"])(resolver)

    def wrapped_resolver(obj, info, *args, **kwargs):
        return decorated_resolver(obj, info, "extra", *args, **kwargs)

    assert await test_authz.resolve(wrapped_resolver, None, None) == "Hello, World!"
