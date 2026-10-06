from fastapi import APIRouter, Depends, Query

from app.deps import provider
from app.routers.schemas import BacklinksIn, BacklinkTargetIn

router = APIRouter(prefix="/api/backlinks", tags=["Backlinks"])


@router.post("/summary", summary="Resumen del perfil de enlaces")
def summary(body: BacklinkTargetIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.backlinks_summary(body.target, confirm=confirm)


@router.post("/list", summary="Listado de backlinks")
def backlinks(body: BacklinksIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.backlinks(body.target, limit=body.limit, mode=body.mode, confirm=confirm)


@router.post("/referring-domains", summary="Dominios de referencia")
def referring_domains(body: BacklinkTargetIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.referring_domains(body.target, limit=body.limit, confirm=confirm)


@router.post("/anchors", summary="Textos ancla")
def anchors(body: BacklinkTargetIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.anchors(body.target, limit=body.limit, confirm=confirm)
