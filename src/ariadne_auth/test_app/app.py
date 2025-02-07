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
from ariadne_auth.test_app.test_data import FACTIONS, SHIPS
from ariadne_auth.types import HasPermissions, PermissionsList

BASE_DIR = Path(__file__).parent

schema = load_schema_from_path(BASE_DIR / "schema.graphql")


# Prepare object with required has_permissions method
@dataclasses.dataclass
class User:
    id: int
    username: str
    permissions: list[str]

    def has_permissions(self, permissions: PermissionsList) -> bool:
        return all(permission in self.permissions for permission in permissions)


# Configure AuthorizationExtension
def get_permission_obj(info: GraphQLResolveInfo) -> HasPermissions:
    return info.context["user"]


authz = AuthorizationExtension(permission_obj=get_permission_obj)
authz.set_required_global_permissions(["user:logged_in"])


query = QueryType()
ship = ObjectType("Ship")
faction = ObjectType("Faction")


@query.field("ships")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ships(obj, *_):
    return SHIPS


@ship.field("name")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ship_name(obj, *_):
    return obj["name"]


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
        _auth.assert_permissions(["read:ships"])

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


# Introduce to context value an object with "has_permissions" method
def get_context_value(request, data):
    user_id = "2"
    return {
        "user": USERS.get(user_id, User(id=0, username="anonymous", permissions=[])),
    }


app = GraphQL(
    make_executable_schema(schema, ship, query, faction),
    context_value=get_context_value,
    http_handler=GraphQLHTTPHandler(extensions=[authz]),  # add the authz extension
    debug=True,
)
