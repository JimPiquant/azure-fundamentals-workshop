import json
import logging
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

app = func.FunctionApp()

# ORDERS_STORAGE_URL holds only the account address. The function's managed identity supplies the access.
def save(container: str, name: str, document: dict) -> None:
    blobs = BlobServiceClient(os.environ["ORDERS_STORAGE_URL"], DefaultAzureCredential())
    # The blob name is the order ID, so processing an order twice overwrites one blob instead of duplicating it.
    blobs.get_blob_client(container, name).upload_blob(
        json.dumps(document),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )


@app.event_hub_message_trigger(
    arg_name="event", event_hub_name="orders", connection="EventHubConnection"
)
def process_order(event: func.EventHubEvent):
    body = event.get_body().decode("utf-8")
    try:
        order = json.loads(body)
    except ValueError:
        save("failed-orders", f"unreadable-{event.sequence_number}.json", {"body": body, "reason": "not valid JSON"})
        logging.warning("Event %s isn't valid JSON; saved to failed-orders", event.sequence_number)
        return

    order_id = order.get("orderId") or f"unknown-{event.sequence_number}"
    logging.info("Processing order %s", order_id)

    problems = []
    if not order.get("storeId"):
        problems.append("storeId is required")
    items = order.get("items") or []
    if not items or any(int(item.get("quantity", 0)) <= 0 for item in items):
        problems.append("every item needs a quantity greater than 0")

    if problems:
        save("failed-orders", f"{order_id}.json", {"order": order, "reason": "; ".join(problems)})
        logging.warning("Order %s failed validation: %s", order_id, "; ".join(problems))
        return

    order["status"] = "Processed"
    save("processed-orders", f"{order_id}.json", order)
    logging.info("Order %s written to processed-orders", order_id)
