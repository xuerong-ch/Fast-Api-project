# main.py
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse # Importante para la redirección
from typing import List, Optional
from datetime import datetime, timezone

# Importas tus modelos desde el archivo modelos.py
from modelo import Tarea, TareaCrear, TareaActualizar

app = FastAPI(
    title="API de Lista de Tareas",
    description="Una API simple para gestionar una lista de tareas pendientes.",
    version="0.1.2", # Versión incrementada
)

# --- Simulación de base de datos en memoria ---
db_tareas: List[Tarea] = []
siguiente_id_tarea: int = 1
# --------------------------------------------

# --- Funciones auxiliares (opcional, pero puede ayudar a organizar) ---
def encontrar_tarea_por_id(id_tarea: int) -> Optional[Tarea]:
    """Busca una tarea por su ID en la base de datos en memoria."""
    for tarea in db_tareas:
        if tarea.id == id_tarea:
            return tarea
    return None

# --- Endpoints de la API ---

@app.get("/", include_in_schema=False) # Raíz para redirigir a /docs
async def redirigir_a_docs():
    """
    Redirige automáticamente la ruta raíz ("/") a la documentación interactiva ("/docs").
    """
    return RedirectResponse(url="/docs")


@app.post("/tareas/", response_model=Tarea, status_code=status.HTTP_201_CREATED, tags=["Tareas"])
async def crear_nueva_tarea(tarea_para_crear: TareaCrear):
    """
    Crea una nueva tarea.

    - **titulo**: El título de la tarea (obligatorio).
    - **descripcion**: Descripción opcional de la tarea.
    - **fecha_finalizacion_propuesta**: Opcional. Si se proporciona, la tarea se crea
      como completada con esta fecha (UTC). La fecha no puede ser anterior al momento de creación.
      Si no se proporciona, la tarea se crea como pendiente.
    """
    global siguiente_id_tarea
    
    fecha_finalizacion_calculada: Optional[datetime] = None
    fecha_creacion_actual = datetime.now(timezone.utc) 
    
    if tarea_para_crear.fecha_finalizacion_propuesta:
        fecha_finalizacion_calculada = tarea_para_crear.fecha_finalizacion_propuesta
        if fecha_finalizacion_calculada < fecha_creacion_actual:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de finalización propuesta no puede ser anterior a la fecha de creación actual."
            )

    try:
        nueva_tarea = Tarea(
            id=siguiente_id_tarea,
            titulo=tarea_para_crear.titulo,
            descripcion=tarea_para_crear.descripcion,
            fecha_creacion=fecha_creacion_actual,
            fecha_finalizacion=fecha_finalizacion_calculada
        )
    except ValueError as e: 
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación al crear la tarea: {str(e)}"
        )
        
    db_tareas.append(nueva_tarea)
    siguiente_id_tarea += 1
    return nueva_tarea

@app.get("/tareas/", response_model=List[Tarea], tags=["Tareas"])
async def obtener_todas_las_tareas():
    """
    Obtiene una lista de todas las tareas almacenadas.
    """
    return db_tareas

@app.get("/tareas/{id_tarea}", response_model=Tarea, tags=["Tareas"])
async def obtener_tarea_especifica(id_tarea: int):
    """
    Obtiene una tarea específica por su ID.
    """
    tarea_encontrada = encontrar_tarea_por_id(id_tarea)
    if not tarea_encontrada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tarea con ID {id_tarea} no encontrada.")
    return tarea_encontrada

@app.put("/tareas/{id_tarea}", response_model=Tarea, tags=["Tareas"])
async def actualizar_tarea_existente(id_tarea: int, tarea_actualizada_datos: TareaActualizar):
    """
    Actualiza una tarea existente.

    Permite modificar título, descripción y estado de completitud.
    - **establecer_completada**: True para completar, False para reabrir.
    - **nueva_fecha_finalizacion**: Fecha específica si se completa o se modifica una existente.
      Si se completa y no se provee, se usa la fecha actual (UTC).
    """
    tarea_existente = encontrar_tarea_por_id(id_tarea)
    if not tarea_existente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tarea con ID {id_tarea} no encontrada.")

    update_data = tarea_actualizada_datos.model_dump(exclude_unset=True)
    
    if "titulo" in update_data:
        tarea_existente.titulo = update_data["titulo"]
    if "descripcion" in update_data:
        tarea_existente.descripcion = update_data.get("descripcion")


    if "establecer_completada" in update_data:
        if update_data["establecer_completada"] is True:
            if not tarea_existente.fecha_finalizacion: 
                tarea_existente.fecha_finalizacion = update_data.get("nueva_fecha_finalizacion") or datetime.now(timezone.utc)
            elif "nueva_fecha_finalizacion" in update_data : 
                 tarea_existente.fecha_finalizacion = update_data.get("nueva_fecha_finalizacion") 
        elif update_data["establecer_completada"] is False:
            tarea_existente.fecha_finalizacion = None
    
    elif "nueva_fecha_finalizacion" in update_data:
        tarea_existente.fecha_finalizacion = update_data.get("nueva_fecha_finalizacion")

    try:
        tarea_validada = Tarea.model_validate(tarea_existente.model_dump())
        
        for i, t in enumerate(db_tareas):
            if t.id == id_tarea:
                db_tareas[i] = tarea_validada
                return tarea_validada
                
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación al actualizar la tarea: {str(e)}"
        )
    
    return tarea_existente


@app.delete("/tareas/{id_tarea}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tareas"])
async def eliminar_tarea_existente(id_tarea: int):
    """
    Elimina una tarea específica por su ID.
    """
    global db_tareas 

    tarea_a_eliminar = encontrar_tarea_por_id(id_tarea)
    if not tarea_a_eliminar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tarea con ID {id_tarea} no encontrada.")
    
    db_tareas = [tarea for tarea in db_tareas if tarea.id != id_tarea]
    
    return

# --- Para ejecutar la aplicación (guardar como main.py y correr en la terminal): ---
# uvicorn main:app --reload
# Luego abrir en el navegador: http://127.0.0.1:8000/docs (o solo http://127.0.0.1:8000/)
