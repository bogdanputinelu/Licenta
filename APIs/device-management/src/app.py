from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

app = FastAPI(title="Device Management API", description="A simple device management demo API")

devices_store: Dict[str, Dict] = {}


class Device(BaseModel):
    device_id: str
    name: str
    type: str
    status: str = "offline"
    location: Optional[str] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Device Management API", "version": "1.0.0"}


@app.get("/devices")
def get_all_devices():
    """Get all devices"""
    return {"devices": list(devices_store.values()), "count": len(devices_store)}


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    """Get a specific device by ID"""
    if device_id not in devices_store:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return devices_store[device_id]


@app.post("/devices")
def create_device(device: Device):
    """Create a new device"""
    if device.device_id in devices_store:
        raise HTTPException(status_code=400, detail=f"Device '{device.device_id}' already exists")

    device_data = device.dict()
    device_data["created_at"] = datetime.now().isoformat()
    device_data["updated_at"] = datetime.now().isoformat()

    devices_store[device.device_id] = device_data
    return {"message": f"Device '{device.device_id}' created successfully", "device": device_data}


@app.put("/devices/{device_id}")
def update_device(device_id: str, device_update: DeviceUpdate):
    """Update an existing device"""
    if device_id not in devices_store:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    update_data = device_update.dict(exclude_unset=True)
    devices_store[device_id].update(update_data)
    devices_store[device_id]["updated_at"] = datetime.now().isoformat()

    return {"message": f"Device '{device_id}' updated successfully", "device": devices_store[device_id]}


@app.delete("/devices/{device_id}")
def delete_device(device_id: str):
    """Delete a device"""
    if device_id not in devices_store:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    deleted_device = devices_store.pop(device_id)
    return {"message": f"Device '{device_id}' deleted successfully", "deleted_device": deleted_device}
