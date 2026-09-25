from collections.abc import Iterable
from uuid import UUID


def ordered_location_ids(location_ids: Iterable[UUID]) -> list[UUID]:
    """Return the canonical lock order for inventory locations."""
    return sorted(location_ids, key=str)
