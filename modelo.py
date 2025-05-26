# modelos.py
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, computed_field
from typing import Optional
from datetime import datetime, timezone

class TareaBase(BaseModel):
    """Modelo base con campos comunes para una tarea."""
    titulo: str = Field(..., min_length=3, max_length=100, description="El título principal de la tarea.")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción detallada opcional de la tarea.")

class TareaCrear(TareaBase):
    """
    Modelo para los datos esperados al crear una nueva tarea.
    Si se proporciona 'fecha_finalizacion_propuesta', la tarea se considera
    creada como completada con esa fecha.
    """
    fecha_finalizacion_propuesta: Optional[datetime] = Field(None, description="Fecha de finalización propuesta. Si se proporciona, la tarea se crea como completada con esta fecha. Si es None, se crea como pendiente.")

    @model_validator(mode='after') 
    def asegurar_utc_propuesta_finalizacion(self) -> 'TareaCrear':
        if self.fecha_finalizacion_propuesta and self.fecha_finalizacion_propuesta.tzinfo is None:
            self.fecha_finalizacion_propuesta = self.fecha_finalizacion_propuesta.replace(tzinfo=timezone.utc)
        return self

class TareaActualizar(BaseModel):
    """
    Modelo para los datos esperados al actualizar una tarea.
    Todos los campos son opcionales, permitiendo actualizaciones parciales.
    """
    titulo: Optional[str] = Field(None, min_length=3, max_length=100, description="Nuevo título de la tarea.")
    descripcion: Optional[str] = Field(None, max_length=500, description="Nueva descripción de la tarea.")

    establecer_completada: Optional[bool] = Field(None, description="Establecer a True para completar, False para reabrir/marcar como pendiente. Si no se envía, el estado no cambia por este flag.")
    nueva_fecha_finalizacion: Optional[datetime] = Field(None, description="Nueva fecha de finalización si se establece como completada o se quiere modificar la existente. Si es None y se completa, se usa la fecha actual.")

    @model_validator(mode='after')
    def validar_actualizacion_finalizacion(self) -> 'TareaActualizar':
        if self.establecer_completada is False and self.nueva_fecha_finalizacion is not None:
            raise ValueError("No se puede especificar una nueva_fecha_finalizacion si se está marcando la tarea como no completada (pendiente).")
        if self.nueva_fecha_finalizacion and self.nueva_fecha_finalizacion.tzinfo is None:
            self.nueva_fecha_finalizacion = self.nueva_fecha_finalizacion.replace(tzinfo=timezone.utc)
        return self


class Tarea(TareaBase):
    """
    Modelo completo de la tarea, como se almacenará y se devolverá en las respuestas.
    El campo 'completada' es derivado de 'fecha_finalizacion' y la fecha actual.
    """
    id: int = Field(..., description="Identificador único de la tarea.")
    fecha_creacion: datetime = Field(description="Fecha y hora de creación de la tarea (UTC).")
    fecha_finalizacion: Optional[datetime] = Field(None, description="Fecha y hora de finalización de la tarea (UTC), si está completada.")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def completada(self) -> bool:
        """
        Indica si la tarea está completada.
        Es True si fecha_finalizacion tiene un valor Y esa fecha es anterior o igual a la fecha y hora actual (UTC).
        Es False si fecha_finalizacion es None o es una fecha futura.
        """
        if self.fecha_finalizacion is None:
            return False
        
        # Asegurarse de que ambas fechas son conscientes de la zona horaria para una comparación correcta
        fecha_finalizacion_utc = self.fecha_finalizacion
        if fecha_finalizacion_utc.tzinfo is None:
            fecha_finalizacion_utc = fecha_finalizacion_utc.replace(tzinfo=timezone.utc)
            
        ahora_utc = datetime.now(timezone.utc)
        
        return fecha_finalizacion_utc <= ahora_utc

    @model_validator(mode='after')
    def validar_coherencia_fechas(self) -> 'Tarea':
        if self.fecha_finalizacion:
            fecha_creacion_utc = self.fecha_creacion
            if fecha_creacion_utc.tzinfo is None:
                 fecha_creacion_utc = fecha_creacion_utc.replace(tzinfo=timezone.utc)

            fecha_finalizacion_utc = self.fecha_finalizacion
            if fecha_finalizacion_utc.tzinfo is None:
                fecha_finalizacion_utc = fecha_finalizacion_utc.replace(tzinfo=timezone.utc)

            if fecha_finalizacion_utc < fecha_creacion_utc:
                raise ValueError("La fecha de finalización no puede ser anterior a la fecha de creación.")
        return self

    @field_validator('fecha_creacion', 'fecha_finalizacion', mode='before')
    @classmethod
    def asegurar_utc_en_entrada(cls, v: Optional[datetime]) -> Optional[datetime]:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
