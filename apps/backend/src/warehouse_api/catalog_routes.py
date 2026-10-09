from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from warehouse_api.auth import Actor, require_work_item_planner
from warehouse_api.catalog import list_skus
from warehouse_api.db import get_db_session
from warehouse_api.schemas import SkuCatalogResponse

router = APIRouter(prefix="/api/v1/skus", tags=["sku-catalog"])


@router.get("", response_model=SkuCatalogResponse)
def read_skus(
    session: Annotated[Session, Depends(get_db_session)],
    _actor: Annotated[Actor, Depends(require_work_item_planner)],
) -> SkuCatalogResponse:
    return list_skus(session)
