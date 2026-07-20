import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connections
from core.models import WifiTicket


class Command(BaseCommand):
    help = 'Sync WiFi tickets with RADIUS: activate started sessions, mark expired tickets (sqlcounter enforces limits)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would happen without making changes')
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        now = timezone.now()
        removed = 0
        activated = 0

        try:
            cursor = connections['radius'].cursor()

            # ----------------------------------------------------------------
            # STEP 1: Detect first connections from radacct and activate tickets
            # ----------------------------------------------------------------
            tickets_a_activer = WifiTicket.objects.filter(
                date_premiere_connexion__isnull=True,
                is_used=False
            )
            for ticket in tickets_a_activer:
                cursor.execute(
                    "SELECT acctstarttime FROM radacct WHERE username = %s ORDER BY acctstarttime ASC LIMIT 1",
                    [ticket.identifiant]
                )
                row = cursor.fetchone()
                if row and row[0]:
                    premiere_connexion = row[0]
                    if premiere_connexion.tzinfo is None:
                        premiere_connexion = premiere_connexion.replace(tzinfo=datetime.timezone.utc)
                    expiration = premiere_connexion + timezone.timedelta(minutes=ticket.ticket_type.duree_minutes)
                    if verbose:
                        self.stdout.write(f'Activating {ticket.identifiant}: started={premiere_connexion}, expires={expiration}')
                    if not dry_run:
                        ticket.date_premiere_connexion = premiere_connexion
                        ticket.date_expiration = expiration
                        ticket.is_used = True
                        ticket.save(update_fields=['date_premiere_connexion', 'date_expiration', 'is_used'])

                        # Update Session-Timeout in radcheck and radreply to match actual remaining time
                        remaining_seconds = max(0, int((expiration - now).total_seconds()))
                        cursor.execute(
                            "UPDATE radcheck SET value = %s WHERE username = %s AND attribute = 'Session-Timeout'",
                            [str(remaining_seconds), ticket.identifiant]
                        )
                        cursor.execute(
                            "UPDATE radreply SET value = %s WHERE username = %s AND attribute = 'Session-Timeout'",
                            [str(remaining_seconds), ticket.identifiant]
                        )
                    activated += 1

            # ----------------------------------------------------------------
            # STEP 2: Remove tickets that were never used after 24h grace period
            # ----------------------------------------------------------------
            never_used_cutoff = now - timezone.timedelta(hours=24)
            tickets_never_used = WifiTicket.objects.filter(
                is_used=False,
                date_premiere_connexion__isnull=True,
                date_creation__lte=never_used_cutoff
            )
            for ticket in tickets_never_used:
                if verbose:
                    self.stdout.write(f'Removing never-used ticket (24h expired): {ticket.identifiant}')
                if not dry_run:
                    cursor.execute("DELETE FROM radcheck WHERE username = %s", [ticket.identifiant])
                    cursor.execute("DELETE FROM radreply WHERE username = %s", [ticket.identifiant])
                    ticket.date_expiration = ticket.date_creation + timezone.timedelta(hours=24)
                    ticket.save(update_fields=['date_expiration'])
                removed += 1

            # ----------------------------------------------------------------
            # STEP 3: Clean stale expired tickets from RADIUS auth tables only
            # ----------------------------------------------------------------
            cleanup_cutoff = now - timezone.timedelta(days=7)
            stale_expired_tickets = WifiTicket.objects.filter(
                date_expiration__lte=cleanup_cutoff,
                is_used=True
            )
            for ticket in stale_expired_tickets:
                username = ticket.identifiant
                if verbose:
                    self.stdout.write(f'Cleaning stale expired ticket from RADIUS: {username} (expired={ticket.date_expiration})')
                if not dry_run:
                    cursor.execute("DELETE FROM radcheck WHERE username = %s", [username])
                    cursor.execute("DELETE FROM radreply WHERE username = %s", [username])
                removed += 1

            if not dry_run:
                connections['radius'].commit()
            cursor.close()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'RADIUS sync failed: {e}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] Would activate {activated} tickets, mark {removed} expired tickets'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Done: activated {activated} tickets, marked {removed} expired tickets in RADIUS'
            ))