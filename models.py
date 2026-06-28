"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re

class BookingCreate(BaseModel):
    booking_date: str = Field(..., description="วันที่จอง (YYYY-MM-DD)")
    slot_start: str = Field(..., description="เวลาเริ่ม (HH:MM)")
    slot_end: str = Field(..., description="เวลาสิ้นสุด (HH:MM)")
    customer_name: str = Field(..., min_length=2, max_length=100, description="ชื่อผู้จอง")
    phone: str = Field(..., description="เบอร์ติดต่อ")
    line_id: Optional[str] = Field(None, max_length=100, description="Line ID")
    condo_name: Optional[str] = Field(None, max_length=200, description="ชื่อคอนโด / โครงการ")
    condo_map_link: Optional[str] = Field(None, max_length=500, description="ลิงก์ Google Maps")
    note: Optional[str] = Field(None, max_length=500, description="หมายเหตุ")

    @field_validator("booking_date")
    @classmethod
    def validate_date(cls, v):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("รูปแบบวันที่ไม่ถูกต้อง (YYYY-MM-DD)")
        # Basic sanity: not in the past? Allow today.
        return v

    @field_validator("slot_start")
    @classmethod
    def validate_slot_start(cls, v):
        import config
        valid_starts = [s["start"] for s in config.SLOTS]
        if v not in valid_starts:
            raise ValueError(f"Slot เริ่มเวลาได้แค่ {', '.join(valid_starts)}")
        return v

    @field_validator("slot_end")
    @classmethod
    def validate_slot_end(cls, v, info):
        import config
        slot_start = info.data.get("slot_start")
        if slot_start:
            # Validate that (slot_start, slot_end) is a valid pair
            from config import is_valid_slot
            if not is_valid_slot(slot_start, v):
                raise ValueError(f"Slot สิ้นสุดต้องเป็น 3 ชั่วโมงหลังจากเริ่ม ({slot_start} → ต้องเป็น {slot_start[:2]}:00 + 3 ชม.)")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^0\d{8,9}$", cleaned):
            raise ValueError("เบอร์โทรศัพท์ไม่ถูกต้อง (ต้องเป็นเบอร์ไทย 9-10 หลัก)")
        return cleaned

    @field_validator("customer_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("ชื่อต้องมีอย่างน้อย 2 ตัวอักษร")
        return v


class BookingStatusUpdate(BaseModel):
    status: str = Field(..., description="สถานะใหม่")
    internal_note: Optional[str] = Field(None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid = ["CONFIRMED_PAID", "PAID_PENDING_CONFIRM", "RESERVED_UNPAID", "AVAILABLE"]
        if v not in valid:
            raise ValueError(f"สถานะไม่ถูกต้อง ต้องเป็นหนึ่งใน {valid}")
        return v


class BookingEdit(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None)
    line_id: Optional[str] = Field(None, max_length=100)
    internal_note: Optional[str] = Field(None, max_length=500)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^0\d{8,9}$", cleaned):
            raise ValueError("เบอร์โทรศัพท์ไม่ถูกต้อง")
        return cleaned
