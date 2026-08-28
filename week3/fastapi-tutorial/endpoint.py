import json
from http import HTTPStatus

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import Response


router = APIRouter()


class EventSchema(BaseModel):
    """Event Schema"""

    event_id: str
    event_type: str
    event_data: dict


"""
Becuase of the router, every endpoint in this file is prefixed with /events/
"""


@router.post("/", dependencies=[])
def handle_event(
    data: EventSchema,
) -> Response:
    print(data)

    # Return acceptance response
    return Response(
        content=json.dumps({"message": "Data received!"}),
        status_code=HTTPStatus.ACCEPTED,
    )
