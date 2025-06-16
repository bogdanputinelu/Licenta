from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import uuid

app = FastAPI(title="Hardware Inventory API",
              description="Hardware inventory and equipment procurement for device operations")


hardware_inventory: Dict[str, Dict] = {}
procurement_requests: Dict[str, Dict] = {}


class HardwareItem(BaseModel):
    item_id: str
    name: str
    category: str  # server, network, storage, spare_parts, cables, etc.
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: int
    location: Optional[str] = None  # datacenter, warehouse, site_a, etc.
    status: str = "available"  # available, deployed, maintenance, retired


class HardwareUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: Optional[int] = None
    location: Optional[str] = None
    status: Optional[str] = None


class ProcurementRequest(BaseModel):
    equipment_name: str
    category: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity: int
    justification: str  # device replacement, capacity expansion, new deployment
    requested_by: str
    target_location: Optional[str] = None
    priority: str = "normal"  # low, normal, high, critical
    estimated_cost: Optional[float] = None


class ProcurementUpdate(BaseModel):
    status: str  # pending, approved, ordered, received, deployed


@app.get("/")
def read_root():
    return {"message": "Hardware Inventory API - Device Operations System", "version": "1.0.0"}


@app.get("/hardware")
def get_hardware_inventory():
    """Get all hardware inventory items"""
    return {
        "hardware": list(hardware_inventory.values()),
        "total_items": len(hardware_inventory),
        "summary": _get_inventory_summary()
    }


@app.get("/hardware/low-stock")
def get_low_stock_items(threshold: int = 5):
    """Get hardware items with low stock levels"""
    low_stock = [
        item for item in hardware_inventory.values()
        if item["quantity"] <= threshold and item["status"] == "available"
    ]
    return {"low_stock_items": low_stock, "count": len(low_stock), "threshold": threshold}


@app.get("/hardware/by-location/{location}")
def get_hardware_by_location(location: str):
    """Get hardware inventory for specific location"""
    location_items = [
        item for item in hardware_inventory.values()
        if item.get("location", "").lower() == location.lower()
    ]
    return {"location": location, "items": location_items, "count": len(location_items)}


@app.get("/hardware/{item_id}")
def get_hardware_item(item_id: str):
    """Get specific hardware item details"""
    if item_id not in hardware_inventory:
        raise HTTPException(status_code=404, detail=f"Hardware item '{item_id}' not found")
    return hardware_inventory[item_id]


@app.post("/hardware")
def add_hardware_item(item: HardwareItem):
    """Add new hardware to inventory"""
    if item.item_id in hardware_inventory:
        raise HTTPException(status_code=400, detail=f"Hardware item '{item.item_id}' already exists")

    item_data = item.dict()
    item_data["added_at"] = datetime.now().isoformat()
    item_data["last_updated"] = datetime.now().isoformat()

    hardware_inventory[item.item_id] = item_data
    return {"message": f"Hardware item '{item.item_id}' added to inventory", "item": item_data}


@app.put("/hardware/{item_id}")
def update_hardware_item(item_id: str, item_update: HardwareUpdate):
    """Update hardware item (quantity, location, status, etc.)"""
    if item_id not in hardware_inventory:
        raise HTTPException(status_code=404, detail=f"Hardware item '{item_id}' not found")

    update_data = item_update.dict(exclude_unset=True)
    hardware_inventory[item_id].update(update_data)
    hardware_inventory[item_id]["last_updated"] = datetime.now().isoformat()

    return {"message": f"Hardware item '{item_id}' updated", "item": hardware_inventory[item_id]}


@app.delete("/hardware/{item_id}")
def remove_hardware_item(item_id: str):
    """Remove hardware item from inventory"""
    if item_id not in hardware_inventory:
        raise HTTPException(status_code=404, detail=f"Hardware item '{item_id}' not found")

    removed_item = hardware_inventory.pop(item_id)
    return {"message": f"Hardware item '{item_id}' removed from inventory", "removed_item": removed_item}





@app.get("/procurement")
def get_procurement_requests():
    """Get all equipment procurement requests"""
    return {
        "requests": list(procurement_requests.values()),
        "total_requests": len(procurement_requests),
        "summary": _get_procurement_summary()
    }


@app.get("/procurement/urgent")
def get_urgent_requests():
    """Get high priority and critical procurement requests"""
    urgent_requests = [
        req for req in procurement_requests.values()
        if req["priority"] in ["high", "critical"] and req["status"] in ["pending", "approved"]
    ]
    return {"urgent_requests": urgent_requests, "count": len(urgent_requests)}


@app.get("/procurement/{request_id}")
def get_procurement_request(request_id: str):
    """Get specific procurement request details"""
    if request_id not in procurement_requests:
        raise HTTPException(status_code=404, detail=f"Procurement request '{request_id}' not found")
    return procurement_requests[request_id]


@app.post("/procurement")
def create_procurement_request(request: ProcurementRequest):
    """Submit new equipment procurement request"""
    request_id = f"PR-{str(uuid.uuid4())[:8].upper()}"

    request_data = request.dict()
    request_data["request_id"] = request_id
    request_data["status"] = "pending"
    request_data["submitted_at"] = datetime.now().isoformat()
    request_data["last_updated"] = datetime.now().isoformat()

    procurement_requests[request_id] = request_data
    return {"message": f"Procurement request '{request_id}' submitted", "request": request_data}


@app.put("/procurement/{request_id}")
def update_procurement_status(request_id: str, status_update: ProcurementUpdate):
    """Update procurement request status"""
    if request_id not in procurement_requests:
        raise HTTPException(status_code=404, detail=f"Procurement request '{request_id}' not found")

    valid_statuses = ["pending", "approved", "ordered", "received", "deployed"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    procurement_requests[request_id]["status"] = status_update.status
    procurement_requests[request_id]["last_updated"] = datetime.now().isoformat()

    return {
        "message": f"Procurement request '{request_id}' status updated to '{status_update.status}'",
        "request": procurement_requests[request_id]
    }


def _get_inventory_summary():
    """Generate inventory summary statistics"""
    if not hardware_inventory:
        return {}

    categories = {}
    statuses = {}
    total_quantity = 0

    for item in hardware_inventory.values():
        # Count by category
        cat = item["category"]
        categories[cat] = categories.get(cat, 0) + item["quantity"]

        # Count by status
        status = item["status"]
        statuses[status] = statuses.get(status, 0) + item["quantity"]

        total_quantity += item["quantity"]

    return {
        "total_quantity": total_quantity,
        "by_category": categories,
        "by_status": statuses
    }


def _get_procurement_summary():
    """Generate procurement summary statistics"""
    if not procurement_requests:
        return {}

    statuses = {}
    priorities = {}

    for req in procurement_requests.values():
        # Count by status
        status = req["status"]
        statuses[status] = statuses.get(status, 0) + 1

        # Count by priority
        priority = req["priority"]
        priorities[priority] = priorities.get(priority, 0) + 1

    return {
        "by_status": statuses,
        "by_priority": priorities
    }