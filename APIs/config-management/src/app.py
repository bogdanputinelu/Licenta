from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI(title="Config Management API", description="A simple config management demo API")

config_store: Dict[str, Any] = {}


class ConfigItem(BaseModel):
    key: str
    value: Any


class ConfigUpdate(BaseModel):
    value: Any


@app.get("/")
def read_root():
    return {"message": "Config Management API", "version": "1.0.0"}


@app.get("/configs")
def get_all_configs():
    """Get all configuration items"""
    return {"configs": config_store, "count": len(config_store)}


@app.get("/configs/{key}")
def get_config(key: str):
    """Get a specific configuration item by key"""
    if key not in config_store:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return {"key": key, "value": config_store[key]}


@app.post("/configs")
def create_config(config: ConfigItem):
    """Create a new configuration item"""
    if config.key in config_store:
        raise HTTPException(status_code=400, detail=f"Config key '{config.key}' already exists")
    config_store[config.key] = config.value
    return {"message": f"Config '{config.key}' created successfully", "key": config.key, "value": config.value}


@app.put("/configs/{key}")
def update_config(key: str, config_update: ConfigUpdate):
    """Update an existing configuration item"""
    if key not in config_store:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    config_store[key] = config_update.value
    return {"message": f"Config '{key}' updated successfully", "key": key, "value": config_update.value}


@app.delete("/configs/{key}")
def delete_config(key: str):
    """Delete a configuration item"""
    if key not in config_store:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    deleted_value = config_store.pop(key)
    return {"message": f"Config '{key}' deleted successfully", "deleted_key": key, "deleted_value": deleted_value}