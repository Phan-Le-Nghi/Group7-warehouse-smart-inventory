from sqlalchemy import select
from sqlalchemy.orm import Session

from warehouse_api.models import Sku
from warehouse_api.schemas import SkuCatalogItem, SkuCatalogResponse


def list_skus(session: Session) -> SkuCatalogResponse:
    skus = session.scalars(select(Sku).order_by(Sku.code, Sku.id)).all()
    return SkuCatalogResponse(
        items=[SkuCatalogItem(sku_id=sku.id, sku=sku.code) for sku in skus]
    )
