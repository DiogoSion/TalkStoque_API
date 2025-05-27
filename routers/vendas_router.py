from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import SessionLocal
from auth_utils import get_current_active_funcionario

router = APIRouter(
    prefix="/vendas",
    tags=["Vendas"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Venda, status_code=status.HTTP_201_CREATED)
def create_venda(
    venda_data: schemas.VendaCreate, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == venda_data.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pedido com id {venda_data.pedido_id} não encontrado.")
    if pedido.venda:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pedido com id {venda_data.pedido_id} já possui uma venda associada.")

    if venda_data.funcionario_id:
        funcionario_db_check = db.query(models.Funcionario).filter(models.Funcionario.id == venda_data.funcionario_id).first()
        if not funcionario_db_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Funcionário com id {venda_data.funcionario_id} não encontrado.")

    db_venda = models.Venda(**venda_data.model_dump())
    db.add(db_venda)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao criar venda: {str(e)}")
    db.refresh(db_venda)
    return db_venda

@router.get("/{venda_id}", response_model=schemas.Venda)
def read_venda(
    venda_id: int, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_venda = db.query(models.Venda).filter(models.Venda.id == venda_id).first()
    if db_venda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda não encontrada")
    return db_venda

@router.get("/", response_model=List[schemas.Venda])
def read_vendas(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    vendas = db.query(models.Venda).offset(skip).limit(limit).all()
    return vendas

@router.put("/{venda_id}", response_model=schemas.Venda)
def update_venda(
    venda_id: int, 
    venda_update: schemas.VendaUpdate, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_venda = db.query(models.Venda).filter(models.Venda.id == venda_id).first()
    if db_venda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda não encontrada")

    update_data = venda_update.model_dump(exclude_unset=True)
    if "funcionario_id" in update_data and update_data["funcionario_id"] is not None:
        funcionario_check = db.query(models.Funcionario).filter(models.Funcionario.id == update_data["funcionario_id"]).first()
        if not funcionario_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Funcionário com id {update_data['funcionario_id']} não encontrado.")

    for key, value in update_data.items():
        setattr(db_venda, key, value)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao atualizar venda: {str(e)}")
    db.refresh(db_venda)
    return db_venda

@router.delete("/{venda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venda(
    venda_id: int, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_venda = db.query(models.Venda).filter(models.Venda.id == venda_id).first()
    if db_venda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda não encontrada")
    db.delete(db_venda)
    db.commit()
    return