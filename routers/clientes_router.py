from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import SessionLocal
from auth_utils import get_current_active_funcionario

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Cliente, status_code=status.HTTP_201_CREATED)
def create_cliente(
    cliente: schemas.ClienteCreate, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_cliente = models.Cliente(**cliente.model_dump())
    db.add(db_cliente)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao criar cliente: {str(e)}")
    db.refresh(db_cliente)
    return db_cliente

@router.get("/{cliente_id}", response_model=schemas.Cliente)
def read_cliente(
    cliente_id: int, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return db_cliente

@router.get("/", response_model=List[schemas.Cliente])
def read_clientes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    clientes = db.query(models.Cliente).offset(skip).limit(limit).all()
    return clientes

@router.put("/{cliente_id}", response_model=schemas.Cliente)
def update_cliente(
    cliente_id: int, 
    cliente_update: schemas.ClienteUpdate, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    
    update_data = cliente_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cliente, key, value)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao atualizar cliente: {str(e)}")
    db.refresh(db_cliente)
    return db_cliente

@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if db_cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    db.delete(db_cliente)
    db.commit()
    return