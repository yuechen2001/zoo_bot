from fastapi import APIRouter, Depends

import db
from deps import get_uid

router = APIRouter(tags=["directory"])

HABITAT_ORDER = [
    "woodland",
    "savanna",
    "tropical",
    "aquatic",
    "tundra",
    "desert",
    "mythic",
    "spectral",
]


@router.get("/directory")
async def get_directory(uid: int = Depends(get_uid)):
    all_species = db.get_all_species()
    owned_ids = db.get_owned_species_ids(uid)

    by_habitat: dict[str, list] = {}
    for s in all_species:
        h = s["habitat"] or "other"
        by_habitat.setdefault(h, []).append(
            {
                "species_id": s["species_id"],
                "name": s["name"],
                "emoji": s["emoji"],
                "rarity": s["rarity"],
                "owned": s["species_id"] in owned_ids,
            }
        )

    for habitat_list in by_habitat.values():
        habitat_list.sort(key=lambda s: (s["rarity"], s["name"]))

    ordered = []
    seen = set()
    for h in HABITAT_ORDER:
        if h in by_habitat:
            ordered.append({"habitat": h, "species": by_habitat[h]})
            seen.add(h)
    for h, species in by_habitat.items():
        if h not in seen:
            ordered.append({"habitat": h, "species": species})

    total = len(all_species)
    discovered = len(owned_ids)
    return {"total": total, "discovered": discovered, "habitats": ordered}
