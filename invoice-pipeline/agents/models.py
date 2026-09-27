from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default



@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float
    amount: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> LineItem:
        return cls(**d)


@dataclass
class TranslatedLineItem:
    description: TranslatedField
    quantity: TranslatedField
    unit_price: TranslatedField
    amount: TranslatedField

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, d: dict) -> TranslatedLineItem:
        return cls(
            description=TranslatedField.from_dict(d.get("description", {})),
            quantity=TranslatedField.from_dict(d.get("quantity", {})),
            unit_price=TranslatedField.from_dict(d.get("unit_price", {})),
            amount=TranslatedField.from_dict(d.get("amount", {})),
        )


@dataclass
class RawInvoice:
    invoice_number: str
    date: str
    vendor: str
    amount: float
    tax: float
    currency: str
    line_items: list[LineItem]
    detected_language: str
    image_key: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "invoice_number": self.invoice_number,
            "date": self.date,
            "vendor": self.vendor,
            "amount": self.amount,
            "tax": self.tax,
            "currency": self.currency,
            "line_items": [li.to_dict() for li in self.line_items],
            "detected_language": self.detected_language,
            "image_key": self.image_key or "",
        }

    @classmethod
    def from_dict(cls, d: dict) -> RawInvoice:
        return cls(
            invoice_number=d.get("invoice_number", ""),
            date=d.get("date", ""),
            vendor=d.get("vendor", ""),
            amount=_to_float(d.get("amount")),
            tax=_to_float(d.get("tax")),
            currency=d.get("currency", ""),
            line_items=[LineItem.from_dict(li) for li in d.get("line_items", [])],
            detected_language=d.get("detected_language", "unknown"),
            image_key=d.get("image_key"),
        )


@dataclass
class TranslatedField:
    value: str
    original: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> TranslatedField:
        return cls(value=str(d.get("value", "")),
                   original=str(d.get("original", "")))


@dataclass
class TranslatedInvoice:
    invoice_number: TranslatedField
    date: TranslatedField
    vendor: TranslatedField
    amount: TranslatedField
    tax: TranslatedField
    currency: TranslatedField
    line_items: list[dict]
    detected_language: str = "en"
    original_language: str = ""
    image_key: str = ""

    def to_dict(self) -> dict:
        return {
            "invoice_number": self.invoice_number.to_dict(),
            "date": self.date.to_dict(),
            "vendor": self.vendor.to_dict(),
            "amount": self.amount.to_dict(),
            "tax": self.tax.to_dict(),
            "currency": self.currency.to_dict(),
            "line_items": self.line_items,
            "detected_language": self.detected_language,
            "original_language": self.original_language,
            "image_key": self.image_key,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TranslatedInvoice:
        return cls(
            invoice_number=TranslatedField.from_dict(d.get("invoice_number", {})),
            date=TranslatedField.from_dict(d.get("date", {})),
            vendor=TranslatedField.from_dict(d.get("vendor", {})),
            amount=TranslatedField.from_dict(d.get("amount", {})),
            tax=TranslatedField.from_dict(d.get("tax", {})),
            currency=TranslatedField.from_dict(d.get("currency", {})),
            line_items=d.get("line_items", []),
            detected_language=d.get("detected_language", "en"),
            original_language=d.get("original_language", ""),
            image_key=d.get("image_key", ""),
        )


@dataclass
class Correction:
    field: str
    original_value: str
    corrected_value: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Correction:
        return cls(
            field=d.get("field", ""),
            original_value=d.get("original_value", d.get("previous_value", "")),
            corrected_value=d.get("corrected_value", ""),
            reason=d.get("reason", ""),
        )


@dataclass
class ValidationReport:
    confidence_score: float
    corrections: list[Correction]
    issues: list[str]

    def to_dict(self) -> dict:
        return {
            "confidence_score": self.confidence_score,
            "corrections": [c.to_dict() for c in self.corrections],
            "issues": self.issues,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ValidationReport:
        return cls(
            confidence_score=_to_float(d.get("confidence_score")),
            corrections=[Correction.from_dict(c) for c in d.get("corrections", [])],
            issues=list(d.get("issues", [])),
        )


@dataclass
class ValidatedInvoice:
    invoice_number: TranslatedField
    date: TranslatedField
    vendor: TranslatedField
    amount: TranslatedField
    tax: TranslatedField
    currency: TranslatedField
    line_items: list[dict]
    validation: ValidationReport
    detected_language: str = "en"
    original_language: str = ""
    image_key: str = ""

    def to_dict(self) -> dict:
        return {
            "invoice_number": self.invoice_number.to_dict(),
            "date": self.date.to_dict(),
            "vendor": self.vendor.to_dict(),
            "amount": self.amount.to_dict(),
            "tax": self.tax.to_dict(),
            "currency": self.currency.to_dict(),
            "line_items": self.line_items,
            "validation": self.validation.to_dict(),
            "detected_language": self.detected_language,
            "original_language": self.original_language,
            "image_key": self.image_key,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ValidatedInvoice:
        return cls(
            invoice_number=TranslatedField.from_dict(d.get("invoice_number", {})),
            date=TranslatedField.from_dict(d.get("date", {})),
            vendor=TranslatedField.from_dict(d.get("vendor", {})),
            amount=TranslatedField.from_dict(d.get("amount", {})),
            tax=TranslatedField.from_dict(d.get("tax", {})),
            currency=TranslatedField.from_dict(d.get("currency", {})),
            line_items=d.get("line_items", []),
            validation=ValidationReport.from_dict(d.get("validation", {})),
            detected_language=d.get("detected_language", "en"),
            original_language=d.get("original_language", ""),
            image_key=d.get("image_key", ""),
        )


@dataclass
class AggregatedReport:
    total_amount: float
    currencies: dict[str, float]
    itemized_summary: dict[str, float]
    discrepancies: list[dict]
    duplicate_flags: list[dict]
    invoice_count: int
    validated_invoices: list[dict]

    def to_dict(self) -> dict:
        return {
            "total_amount": self.total_amount,
            "currencies": self.currencies,
            "itemized_summary": self.itemized_summary,
            "discrepancies": self.discrepancies,
            "duplicate_flags": self.duplicate_flags,
            "invoice_count": self.invoice_count,
            "validated_invoices": self.validated_invoices,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AggregatedReport:
        itemized = d.get("itemized_summary", {})
        if not isinstance(itemized, dict):
            itemized = {
                (item.get("description", "") if isinstance(item, dict) else str(item)): _to_float(
                    item.get("total_line_amount", item.get("amount")) if isinstance(item, dict) else item
                )
                for item in itemized
            }
        return cls(
            total_amount=_to_float(d.get("total_amount")),
            currencies=dict(d.get("currencies", {})),
            itemized_summary=itemized,
            discrepancies=list(d.get("discrepancies", [])),
            duplicate_flags=list(d.get("duplicate_flags", [])),
            invoice_count=_to_int(d.get("invoice_count")),
            validated_invoices=list(d.get("validated_invoices", [])),
        )


@dataclass
class ApprovalResult:
    status: str
    reviewer_notes: str
    approved_by: str
    timestamp: str
    invoice_number: str
    amount: float
    vendor: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ApprovalResult:
        return cls(
            status=d.get("status", "unknown"),
            reviewer_notes=d.get("reviewer_notes", ""),
            approved_by=d.get("approved_by", ""),
            timestamp=d.get("timestamp", ""),
            invoice_number=d.get("invoice_number", ""),
            amount=_to_float(d.get("amount")),
            vendor=d.get("vendor", ""),
        )


@dataclass
class FormattedInvoice:
    invoice_number: str
    status: str
    template: str
    prompt: str
    formatted_image_url: str = ""
    formatted_image_path: str = ""
    invoice_key: str = ""
    vendor: str = ""
    amount: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FormattedInvoice:
        return cls(
            invoice_number=d.get("invoice_number", ""),
            status=d.get("status", "unknown"),
            template=d.get("template", "clean_business_invoice"),
            prompt=d.get("prompt", ""),
            formatted_image_url=d.get("formatted_image_url", ""),
            formatted_image_path=d.get("formatted_image_path", ""),
            invoice_key=d.get("invoice_key", ""),
            vendor=d.get("vendor", ""),
            amount=_to_float(d.get("amount")),
            error=d.get("error", ""),
        )
