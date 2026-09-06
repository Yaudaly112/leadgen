"""Suppression list manager — prevents contacting opted-out leads.

Handles email, phone, and domain-level suppression. All outreach methods
must check this before sending.
"""

import csv
import io
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, or_

from app.models import (
    Lead,
    LeadStatus,
    SuppressionEntry,
    async_session,
)


class SuppressionService:
    """Manages the do-not-contact suppression list."""

    # ── Checking ────────────────────────────────────────────────────────────────

    async def is_suppressed(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> dict:
        """Check if any of the given contact info is suppressed.

        Returns dict with is_suppressed bool and details about what matched.
        """
        async with async_session() as session:
            checks = []

            if email:
                email_lower = email.lower().strip()
                email_domain = email_lower.split("@")[-1] if "@" in email_lower else None

                # Check email suppression
                result = await session.execute(
                    select(SuppressionEntry).where(
                        SuppressionEntry.active == True,
                        SuppressionEntry.contact_type == "email",
                        SuppressionEntry.value == email_lower,
                    )
                )
                email_match = result.scalar_one_or_none()
                if email_match:
                    checks.append({
                        "type": "email",
                        "value": email_match.value,
                        "reason": email_match.reason,
                        "description": email_match.description,
                        "created_at": email_match.created_at.isoformat(),
                    })

                # Check domain suppression
                if email_domain:
                    result = await session.execute(
                        select(SuppressionEntry).where(
                            SuppressionEntry.active == True,
                            SuppressionEntry.contact_type == "domain",
                            SuppressionEntry.value == email_domain,
                        )
                    )
                    domain_match = result.scalar_one_or_none()
                    if domain_match:
                        checks.append({
                            "type": "domain",
                            "value": domain_match.value,
                            "reason": domain_match.reason,
                            "description": domain_match.description,
                            "created_at": domain_match.created_at.isoformat(),
                        })

            if phone:
                phone_normalized = self._normalize_phone(phone)
                result = await session.execute(
                    select(SuppressionEntry).where(
                        SuppressionEntry.active == True,
                        SuppressionEntry.contact_type == "phone",
                        or_(
                            SuppressionEntry.value == phone,
                            SuppressionEntry.value == phone_normalized,
                        ),
                    )
                )
                phone_match = result.scalar_one_or_none()
                if phone_match:
                    checks.append({
                        "type": "phone",
                        "value": phone_match.value,
                        "reason": phone_match.reason,
                        "description": phone_match.description,
                        "created_at": phone_match.created_at.isoformat(),
                    })

            return {
                "is_suppressed": len(checks) > 0,
                "matches": checks,
            }

    async def check_lead(self, lead_id: int) -> dict:
        """Check if a lead's contact info is suppressed."""
        async with async_session() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                return {"is_suppressed": False, "matches": [], "error": "Lead not found"}

        return await self.is_suppressed(email=lead.email, phone=lead.phone)

    # ── Adding ──────────────────────────────────────────────────────────────────

    async def suppress_email(
        self,
        email: str,
        reason: str = "manual",
        description: str = "",
        source: str = "manual",
        lead_id: Optional[int] = None,
        outreach_log_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        added_by: str = "user",
    ) -> dict:
        """Add an email to the suppression list."""
        email_lower = email.lower().strip()
        if not email_lower or "@" not in email_lower:
            return {"error": "Invalid email address"}

        async with async_session() as session:
            # Check if already suppressed
            existing = await session.execute(
                select(SuppressionEntry).where(
                    SuppressionEntry.contact_type == "email",
                    SuppressionEntry.value == email_lower,
                    SuppressionEntry.active == True,
                )
            )
            if existing.scalar_one_or_none():
                return {"status": "already_suppressed", "email": email_lower}

            entry = SuppressionEntry(
                contact_type="email",
                value=email_lower,
                reason=reason,
                description=description,
                source=source,
                lead_id=lead_id,
                outreach_log_id=outreach_log_id,
                campaign_id=campaign_id,
                active=True,
                added_by=added_by,
            )
            session.add(entry)

            # Also update the lead status if linked
            if lead_id:
                lead = await session.get(Lead, lead_id)
                if lead:
                    lead.status = LeadStatus.DO_NOT_CONTACT
                    lead.notes = f"Suppressed: {reason}" + (f" — {description}" if description else "")

            await session.commit()
            await session.refresh(entry)

            return {"status": "suppressed", "id": entry.id, "email": email_lower}

    async def suppress_domain(
        self,
        domain: str,
        reason: str = "manual",
        description: str = "",
        source: str = "manual",
        added_by: str = "user",
    ) -> dict:
        """Suppress an entire email domain."""
        domain_lower = domain.lower().strip().replace("http://", "").replace("https://", "").rstrip("/")
        if not domain_lower:
            return {"error": "Invalid domain"}

        async with async_session() as session:
            existing = await session.execute(
                select(SuppressionEntry).where(
                    SuppressionEntry.contact_type == "domain",
                    SuppressionEntry.value == domain_lower,
                    SuppressionEntry.active == True,
                )
            )
            if existing.scalar_one_or_none():
                return {"status": "already_suppressed", "domain": domain_lower}

            entry = SuppressionEntry(
                contact_type="domain",
                value=domain_lower,
                reason=reason,
                description=description,
                source=source,
                active=True,
                added_by=added_by,
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)

            return {"status": "suppressed", "id": entry.id, "domain": domain_lower}

    async def suppress_phone(
        self,
        phone: str,
        reason: str = "manual",
        description: str = "",
        source: str = "manual",
        lead_id: Optional[int] = None,
        added_by: str = "user",
    ) -> dict:
        """Add a phone number to the suppression list."""
        phone_normalized = self._normalize_phone(phone)
        if not phone_normalized:
            return {"error": "Invalid phone number"}

        async with async_session() as session:
            existing = await session.execute(
                select(SuppressionEntry).where(
                    SuppressionEntry.contact_type == "phone",
                    SuppressionEntry.active == True,
                    or_(
                        SuppressionEntry.value == phone,
                        SuppressionEntry.value == phone_normalized,
                    ),
                )
            )
            if existing.scalar_one_or_none():
                return {"status": "already_suppressed", "phone": phone_normalized}

            entry = SuppressionEntry(
                contact_type="phone",
                value=phone_normalized,
                reason=reason,
                description=description,
                source=source,
                lead_id=lead_id,
                active=True,
                added_by=added_by,
            )
            session.add(entry)

            if lead_id:
                lead = await session.get(Lead, lead_id)
                if lead:
                    lead.status = LeadStatus.DO_NOT_CONTACT
                    lead.notes = f"Suppressed: {reason}" + (f" — {description}" if description else "")

            await session.commit()
            await session.refresh(entry)

            return {"status": "suppressed", "id": entry.id, "phone": phone_normalized}

    # ── Removing ────────────────────────────────────────────────────────────────

    async def unsuppress(self, entry_id: int, removed_by: str = "user") -> dict:
        """Remove a suppression entry (reactivate the contact)."""
        async with async_session() as session:
            entry = await session.get(SuppressionEntry, entry_id)
            if not entry:
                return {"error": "Suppression entry not found"}
            if not entry.active:
                return {"status": "already_inactive"}

            entry.active = False
            entry.removed_by = removed_by
            entry.removed_at = datetime.utcnow()

            # If linked to a lead, restore to previous status
            if entry.lead_id:
                lead = await session.get(Lead, entry.lead_id)
                if lead and lead.status == LeadStatus.DO_NOT_CONTACT:
                    lead.status = LeadStatus.DISCOVERED
                    lead.notes = f"Unsuppressed by {removed_by}"

            await session.commit()
            return {"status": "removed", "id": entry_id}

    # ── Bulk Operations ─────────────────────────────────────────────────────────

    async def bulk_suppress(
        self,
        entries: list[dict],
        source: str = "import",
        added_by: str = "import",
    ) -> dict:
        """Bulk add entries to the suppression list.

        Each entry dict should have: contact_type, value, and optionally reason, description.
        """
        added = 0
        skipped = 0
        errors = 0

        async with async_session() as session:
            for entry_data in entries:
                try:
                    contact_type = entry_data.get("contact_type", "email")
                    value = entry_data.get("value", "").strip()

                    if not value:
                        errors += 1
                        continue

                    if contact_type == "email":
                        value = value.lower()
                    elif contact_type == "phone":
                        value = self._normalize_phone(value)
                    elif contact_type == "domain":
                        value = value.lower().replace("http://", "").replace("https://", "").rstrip("/")

                    # Check if already exists
                    existing = await session.execute(
                        select(SuppressionEntry).where(
                            SuppressionEntry.contact_type == contact_type,
                            SuppressionEntry.value == value,
                            SuppressionEntry.active == True,
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped += 1
                        continue

                    entry = SuppressionEntry(
                        contact_type=contact_type,
                        value=value,
                        reason=entry_data.get("reason", "import"),
                        description=entry_data.get("description", ""),
                        source=source,
                        active=True,
                        added_by=added_by,
                    )
                    session.add(entry)
                    added += 1

                except Exception as e:
                    errors += 1
                    print(f"Error processing suppression entry: {e}")

            await session.commit()

        return {"added": added, "skipped": skipped, "errors": errors}

    async def import_csv(self, csv_content: str, added_by: str = "csv_import") -> dict:
        """Import suppressions from a CSV string.

        Expected columns: contact_type, value, reason (optional), description (optional)
        Or simple format: one email/phone per line (detected as email if contains @)
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        entries = []

        for row in reader:
            # If CSV has contact_type and value columns
            if "contact_type" in row and "value" in row:
                entries.append({
                    "contact_type": row["contact_type"],
                    "value": row["value"],
                    "reason": row.get("reason", "csv_import"),
                    "description": row.get("description", ""),
                })
            # Simple format: just email addresses
            elif "email" in row:
                entries.append({
                    "contact_type": "email",
                    "value": row["email"],
                    "reason": "csv_import",
                })
            elif "value" in row:
                value = row["value"]
                contact_type = "email" if "@" in value else "phone"
                entries.append({
                    "contact_type": contact_type,
                    "value": value,
                    "reason": "csv_import",
                })

        if not entries:
            # Try line-by-line parsing (one value per line)
            for line in csv_content.strip().split("\n"):
                line = line.strip().strip('"').strip("'")
                if not line or line.startswith("#"):
                    continue
                contact_type = "email" if "@" in line else "phone"
                entries.append({
                    "contact_type": contact_type,
                    "value": line,
                    "reason": "csv_import",
                })

        return await self.bulk_suppress(entries, source="csv_import", added_by=added_by)

    async def export_csv(self, active_only: bool = True) -> str:
        """Export suppression list as CSV."""
        async with async_session() as session:
            query = select(SuppressionEntry)
            if active_only:
                query = query.where(SuppressionEntry.active == True)
            query = query.order_by(SuppressionEntry.created_at.desc())

            result = await session.execute(query)
            entries = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["contact_type", "value", "reason", "description", "source", "created_at"])

        for entry in entries:
            writer.writerow([
                entry.contact_type,
                entry.value,
                entry.reason,
                entry.description or "",
                entry.source or "",
                entry.created_at.isoformat() if entry.created_at else "",
            ])

        return output.getvalue()

    # ── Querying ────────────────────────────────────────────────────────────────

    async def list_entries(
        self,
        contact_type: Optional[str] = None,
        reason: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List suppression entries with filters."""
        async with async_session() as session:
            query = select(SuppressionEntry)

            if active_only:
                query = query.where(SuppressionEntry.active == True)
            if contact_type:
                query = query.where(SuppressionEntry.contact_type == contact_type)
            if reason:
                query = query.where(SuppressionEntry.reason == reason)
            if search:
                query = query.where(SuppressionEntry.value.ilike(f"%{search}%"))

            # Count
            count_query = select(func.count(SuppressionEntry.id))
            if active_only:
                count_query = count_query.where(SuppressionEntry.active == True)
            if contact_type:
                count_query = count_query.where(SuppressionEntry.contact_type == contact_type)
            if reason:
                count_query = count_query.where(SuppressionEntry.reason == reason)
            if search:
                count_query = count_query.where(SuppressionEntry.value.ilike(f"%{search}%"))

            total = await session.scalar(count_query) or 0

            query = query.order_by(SuppressionEntry.created_at.desc())
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            entries = result.scalars().all()

            return {
                "total": total,
                "entries": [
                    {
                        "id": e.id,
                        "contact_type": e.contact_type,
                        "value": e.value,
                        "reason": e.reason,
                        "description": e.description,
                        "source": e.source,
                        "lead_id": e.lead_id,
                        "active": e.active,
                        "added_by": e.added_by,
                        "created_at": e.created_at.isoformat(),
                        "removed_at": e.removed_at.isoformat() if e.removed_at else None,
                    }
                    for e in entries
                ],
            }

    async def get_stats(self) -> dict:
        """Get suppression list statistics."""
        async with async_session() as session:
            total_active = await session.scalar(
                select(func.count(SuppressionEntry.id)).where(SuppressionEntry.active == True)
            ) or 0

            by_type = {}
            for ct in ["email", "phone", "domain"]:
                count = await session.scalar(
                    select(func.count(SuppressionEntry.id)).where(
                        SuppressionEntry.active == True,
                        SuppressionEntry.contact_type == ct,
                    )
                ) or 0
                by_type[ct] = count

            by_reason = {}
            for reason in ["unsubscribe", "bounce", "spam_report", "manual", "complaint", "import"]:
                count = await session.scalar(
                    select(func.count(SuppressionEntry.id)).where(
                        SuppressionEntry.active == True,
                        SuppressionEntry.reason == reason,
                    )
                ) or 0
                if count > 0:
                    by_reason[reason] = count

            # Recent additions (last 7 days)
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent = await session.scalar(
                select(func.count(SuppressionEntry.id)).where(
                    SuppressionEntry.active == True,
                    SuppressionEntry.created_at >= week_ago,
                )
            ) or 0

            return {
                "total_active": total_active,
                "by_type": by_type,
                "by_reason": by_reason,
                "recent_7_days": recent,
            }

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize a phone number to digits only with country code."""
        digits = re.sub(r"[^\d]", "", phone)
        if len(digits) == 10:
            digits = "1" + digits  # assume US
        return digits


suppression_service = SuppressionService()
