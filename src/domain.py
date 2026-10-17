"""Deterministic leave-domain rules; this module must never call the model."""
from __future__ import annotations

from datetime import date, timedelta

from .contracts import LeaveBalance, PrepareLeaveArgs


class DomainError(ValueError):
    pass


def business_days(start: date, end: date) -> int:
    """Hitung jumlah hari kerja Senin-Jumat secara inklusif."""
    if end < start:
        raise DomainError("tanggal akhir tidak boleh sebelum tanggal mulai")

    current = start
    total = 0

    while current <= end:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)

    if total == 0:
        raise DomainError("rentang cuti harus memiliki minimal satu hari kerja")

    return total


def validate_leave_request(
    args: PrepareLeaveArgs,
    balances: list[LeaveBalance],
    overlaps: bool,
    today: date,
) -> tuple[int, list[str]]:
    """Validasi aturan deterministik sebelum proposal cuti dibuat."""

    if args.start_date < today:
        raise DomainError("tanggal mulai tidak boleh berada di masa lalu")

    if args.end_date < args.start_date:
        raise DomainError("tanggal akhir tidak boleh sebelum tanggal mulai")

    days = business_days(args.start_date, args.end_date)

    if overlaps:
        raise DomainError(
            "tanggal cuti bertumpang tindih dengan permintaan cuti aktif"
        )

    balance = next(
        (
            item
            for item in balances
            if item.leave_type == args.leave_type
        ),
        None,
    )

    if balance is None:
        raise DomainError(
            f"saldo untuk jenis cuti {args.leave_type} tidak tersedia"
        )

    if days > balance.available_days:
        raise DomainError(
            "saldo cuti tidak cukup untuk rentang tanggal yang diminta"
        )

    summary = [
        f"Jenis cuti: {args.leave_type}",
        f"Jumlah hari kerja: {days}",
        f"Saldo tersedia: {balance.available_days} hari",
        "Tidak ditemukan permintaan cuti aktif yang bertumpang tindih",
    ]

    return days, summary


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_rate: float | None,
    output_rate: float | None,
) -> float | None:
    """Estimasi biaya hanya jika kedua tarif telah dikonfigurasi."""
    if input_rate is None or output_rate is None:
        return None

    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate

    return input_cost + output_cost
