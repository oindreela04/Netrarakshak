from fastapi import APIRouter, Depends

from ai import registry

from ..deps import CurrentUser, get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/modules")
def modules(cu: CurrentUser = Depends(get_current_user)):
    return [registry.availability(k) for k in registry.MODULES]
