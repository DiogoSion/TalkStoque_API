from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import SessionLocal
from auth_utils import get_current_active_funcionario

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Pedido, status_code=status.HTTP_201_CREATED)
def create_pedido(
    pedido_data: schemas.PedidoCreate, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == pedido_data.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cliente com id {pedido_data.cliente_id} não encontrado.")

    pedido_itens_data = pedido_data.itens
    pedido_dict = pedido_data.model_dump(exclude={'itens'})
    db_pedido = models.Pedido(**pedido_dict)
    db.add(db_pedido)
    
    created_itens_models = []
    if pedido_itens_data:
        for item_data in pedido_itens_data:
            produto = db.query(models.Produto).filter(models.Produto.id == item_data.produto_id).first()
            if not produto:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Produto com id {item_data.produto_id} não encontrado.")
            if produto.quantidade_estoque < item_data.quantidade:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Estoque insuficiente para {produto.nome}.")
            
            db_item = models.PedidoItem(**item_data.model_dump()) 
            db_item.pedido = db_pedido # Associa o item ao pedido que está sendo criado
            produto.quantidade_estoque -= item_data.quantidade
            db.add(produto)
            created_itens_models.append(db_item)
        # Adiciona os itens depois que o pedido já está na sessão
        # db.add_all(created_itens_models) # SQLAlchemy pode lidar com isso através do relacionamento e cascade se configurado

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao criar pedido: {str(e)}")
    
    db.refresh(db_pedido)
    return db_pedido

@router.get("/{pedido_id}", response_model=schemas.Pedido)
def read_pedido(
    pedido_id: int, 
    db: Session = Depends(get_db), 
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if db_pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return db_pedido

@router.get("/", response_model=List[schemas.Pedido])
def read_pedidos(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    pedidos = db.query(models.Pedido).offset(skip).limit(limit).all()
    return pedidos

@router.put("/{pedido_id}", response_model=schemas.Pedido)
def update_pedido(
    pedido_id: int, 
    pedido_update: schemas.PedidoUpdate, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if db_pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    update_data = pedido_update.model_dump(exclude_unset=True)
    if "cliente_id" in update_data:
        cliente = db.query(models.Cliente).filter(models.Cliente.id == update_data["cliente_id"]).first()
        if not cliente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cliente com id {update_data['cliente_id']} não encontrado.")

    for key, value in update_data.items():
        setattr(db_pedido, key, value)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao atualizar pedido: {str(e)}")
    db.refresh(db_pedido)
    return db_pedido

@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pedido(
    pedido_id: int, 
    db: Session = Depends(get_db),
    current_funcionario: models.Funcionario = Depends(get_current_active_funcionario)
):
    db_pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if db_pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    
    for item in db_pedido.itens: # type: ignore
        produto = db.query(models.Produto).filter(models.Produto.id == item.produto_id).first()
        if produto:
            produto.quantidade_estoque += item.quantidade
            db.add(produto)

    db.delete(db_pedido)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao deletar pedido: {str(e)}")
    return