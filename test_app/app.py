import dataclasses
from pathlib import Path

from ariadne import (
    ObjectType,
    QueryType,
    load_schema_from_path,
    make_executable_schema,
)
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLHTTPHandler
from graphql import GraphQLResolveInfo

from ariadne_auth.authz import AuthorizationExtension
from ariadne_auth.types import HasPermissions, PermissionsList
from test_app.test_data import FACTIONS, SHIPS

BASE_DIR = Path(__file__).parent

schema = load_schema_from_path(BASE_DIR / "schema.graphql")


@dataclasses.dataclass
class HasPermissionsObj:
    permissions: list[str]

    async def has_permissions(self, permissions: PermissionsList) -> bool:
        return all(permission in self.permissions for permission in permissions)


# Prepare object with required has_permissions method
@dataclasses.dataclass
class User(HasPermissionsObj):
    id: int
    username: str


@dataclasses.dataclass
class Dock(HasPermissionsObj):
    name: str

    def has_permissions(self, permissions: PermissionsList) -> bool:
        return all(permission in self.permissions for permission in permissions)


async def get_dock_as_permission_object_async(
    info: GraphQLResolveInfo,
) -> HasPermissionsObj:
    return Dock(
        name="Dock",
        permissions=[
            "read:shipsInDock",
        ],
    )


# Configure AuthorizationExtension
def get_permission_obj(info: GraphQLResolveInfo) -> HasPermissions:
    return info.context["user"]


authz = AuthorizationExtension(permissions_object_provider_fn=get_permission_obj)
authz.set_required_global_permissions(["user:logged_in"])


query = QueryType()
ship = ObjectType("Ship")
faction = ObjectType("Faction")


@query.field("shipsInDock")
@authz.require_permissions(
    permissions=["read:shipsInDock"],
    ignore_global_permissions=True,
    permissions_object_provider_fn=get_dock_as_permission_object_async,
)
def resolve_ships_in_dock(obj, *_):
    return [_ship for _ship in SHIPS if _ship["in_dock"]]


@query.field("ships")
@authz.require_permissions(
    permissions=[],
    ignore_global_permissions=True,
    permissions_object_provider_fn=get_permission_obj,
)
async def resolve_ships(obj, *_):
    return SHIPS


@ship.field("name")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ship_name(obj, *_):
    return obj["name"]


@ship.field("inDock")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ship_in_dock(obj, *_):
    return obj["in_dock"]


@query.field("rebels")
@authz.require_permissions(permissions=["read:rebels"])
async def resolve_rebels(*_):
    return FACTIONS[0]


@query.field("empire")
@authz.require_permissions(permissions=["read:empire"], ignore_global_permissions=False)
async def resolve_empire(*_):
    return FACTIONS[1]


@faction.field("ships")
async def resolve_faction_ships(faction_obj, info: GraphQLResolveInfo, *_):
    _auth = info.context["auth"]
    if (
        faction_obj["name"] == "Alliance to Restore the Republic"
    ):  # Rebels faction requires additional perm to read ships
        await _auth.assert_permissions_async(
            _auth.permissions_object_provider_fn(info), ["read:ships"]
        )

    return [_ship for _ship in SHIPS if _ship["factionId"] == faction_obj["id"]]


# Application setup
USERS = {
    "1": User(
        id=1,
        username="userEmpire",
        permissions=["user:logged_in", "read:empire"],
    ),
    "2": User(
        id=1,
        username="EmpireSpyRebels",
        permissions=[
            "user:logged_in",
            "read:empire",
            "read:rebels",
        ],  # can't read rebels ships
    ),
}


def get_context_value(request, data):
    user_id = "2"
    return {
        "user": USERS.get(user_id, User(id=0, username="anonymous", permissions=[])),
        **authz.generate_authz_context(request),
    }


app = GraphQL(
    make_executable_schema(schema, ship, query, faction),
    context_value=get_context_value,
    http_handler=GraphQLHTTPHandler(extensions=[authz]),  # add the authz extension
    debug=True,
)
