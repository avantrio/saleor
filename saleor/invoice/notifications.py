from ..account.models import User
from ..core.notify_events import NotifyEventType
from ..invoice import events
from ..plugins.manager import PluginsManager
from .models import Invoice


def get_invoice_payload(invoice):
    return {
        "id": invoice.id,
        "number": invoice.number,
        "download_url": invoice.url,
    }


def send_invoice(invoice: "Invoice", staff_user: "User", manager: "PluginsManager"):
    """Send an invoice to user of related order with URL to download it."""
    payload = {
        "invoice": get_invoice_payload(invoice),
        "recipient_email": invoice.order.get_customer_email(),  # type: ignore
    }
    manager.notify(NotifyEventType.INVOICE_READY, payload)
    manager.invoice_sent(invoice, invoice.order.get_customer_email())  # type: ignore
    events.invoice_sent_event(user=staff_user, invoice=invoice)