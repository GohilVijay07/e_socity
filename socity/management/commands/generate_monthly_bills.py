from decimal import Decimal, InvalidOperation
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models

from socity.models import MaintenanceBill, Unit, Resident


class Command(BaseCommand):
    help = "Generate monthly maintenance bills for units (duplicate-safe)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            help="Billing month in YYYY-MM format. Default is current month.",
        )
        parser.add_argument(
            "--amount",
            type=str,
            default="3000.00",
            help="Bill amount to assign for newly created bills. Default: 3000.00",
        )
        parser.add_argument(
            "--only-occupied",
            action="store_true",
            help="Generate bills only for occupied units.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database.",
        )

    def handle(self, *args, **options):
        billing_month = self._parse_month(options.get("month"))
        amount = self._parse_amount(options.get("amount"))
        only_occupied = options.get("only_occupied", False)
        dry_run = options.get("dry_run", False)

        units_qs = Unit.objects.all().order_by("wing", "unit_no")
        if only_occupied:
            units_qs = units_qs.filter(is_occupied=True)

        units = list(units_qs)
        if not units:
            self.stdout.write(self.style.WARNING("No units found. Nothing to generate."))
            return

        created_count = 0
        skipped_count = 0
        invalid_count = 0

        if dry_run:
            for unit in units:
                # Check if bill already exists
                exists = MaintenanceBill.objects.filter(unit=unit, billing_month=billing_month).exists()
                if exists:
                    skipped_count += 1
                else:
                    # Check if unit has valid residents for this billing month
                    is_valid = self._is_unit_eligible(unit, billing_month)
                    if is_valid:
                        created_count += 1
                    else:
                        invalid_count += 1

            self.stdout.write(self.style.WARNING("Dry run mode: no database changes made."))
            self.stdout.write(
                f"Month: {billing_month} | Units checked: {len(units)} | "
                f"Would create: {created_count} | Already exists: {skipped_count} | Invalid: {invalid_count}"
            )
            return

        with transaction.atomic():
            for unit in units:
                # Check if unit has valid residents for this billing month
                if not self._is_unit_eligible(unit, billing_month):
                    invalid_count += 1
                    continue

                _, created = MaintenanceBill.objects.get_or_create(
                    unit=unit,
                    billing_month=billing_month,
                    defaults={
                        "amount": amount,
                        "penalty": Decimal("0.00"),
                        "status": "PENDING",
                        "bill_date": billing_month,  # Set bill_date to billing_month
                        "is_auto_generated": True,  # Mark as system-generated
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS("Monthly bill generation completed."))
        self.stdout.write(
            f"Month: {billing_month} | Units checked: {len(units)} | "
            f"Created: {created_count} | Already exists: {skipped_count} | Invalid/Ineligible: {invalid_count}"
        )

    def _parse_month(self, month_raw):
        if not month_raw:
            today = date.today()
            return today.replace(day=1)

        parts = month_raw.split("-")
        if len(parts) != 2:
            raise CommandError("Invalid --month format. Use YYYY-MM, e.g. 2026-04")

        try:
            year = int(parts[0])
            month = int(parts[1])
            return date(year, month, 1)
        except ValueError as exc:
            raise CommandError("Invalid --month value. Use YYYY-MM, e.g. 2026-04") from exc

    def _parse_amount(self, amount_raw):
        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError) as exc:
            raise CommandError("Invalid --amount value. Example: --amount 3000.00") from exc

        if amount <= 0:
            raise CommandError("--amount must be greater than 0")

        return amount

    def _is_unit_eligible(self, unit, billing_month):
        """Check if unit has at least one resident who moved in on or before billing_month."""
        residents = Resident.objects.filter(
            unit=unit,
            move_in_date__lte=billing_month,
        )
        # Also check that the resident hasn't moved out before the billing month, 
        # or move_out_date is not set (still living there)
        eligible_residents = residents.filter(
            models.Q(move_out_date__isnull=True) | models.Q(move_out_date__gte=billing_month)
        )
        return eligible_residents.exists()
