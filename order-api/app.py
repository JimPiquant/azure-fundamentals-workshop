import json
import logging
import os
import uuid

from azure.eventhub import EventData, EventHubProducerClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from flask import Flask, jsonify, request

log = logging.getLogger("orders")
log.setLevel(logging.INFO)

app = Flask(__name__)
credential = DefaultAzureCredential()

# Part 1 settings: the API writes each order to Blob Storage.
STORAGE_ACCOUNT_URL = os.environ.get("STORAGE_ACCOUNT_URL")
ORDERS_CONTAINER = os.environ.get("ORDERS_CONTAINER", "orders")

# Part 2 settings: when these exist, the API sends each order to Event Hubs instead.
EVENTHUB_FQDN = os.environ.get("EVENTHUB_FQDN")
EVENTHUB_NAME = os.environ.get("EVENTHUB_NAME", "orders")


@app.get("/")
def health():
    mode = "Event Hubs" if EVENTHUB_FQDN else "Blob Storage"
    return f"Order API is running (orders go to {mode})", 200


@app.post("/orders")
def submit_order():
    order = request.get_json(force=True)
    order_id = order.get("orderId") or f"PX-{uuid.uuid4().hex[:6].upper()}"
    order["orderId"] = order_id

    if EVENTHUB_FQDN:
        producer = EventHubProducerClient(
            fully_qualified_namespace=EVENTHUB_FQDN,
            eventhub_name=EVENTHUB_NAME,
            credential=credential,
        )
        with producer:
            batch = producer.create_batch()
            event = EventData(json.dumps(order))
            event.properties = {"orderId": order_id}
            batch.add(event)
            producer.send_batch(batch)
        log.info("Order %s sent to Event Hubs for store %s", order_id, order.get("storeId"))
        return jsonify({"orderId": order_id, "status": "Accepted"}), 202

    if STORAGE_ACCOUNT_URL:
        order["status"] = "Received"
        blob = BlobServiceClient(STORAGE_ACCOUNT_URL, credential).get_blob_client(
            ORDERS_CONTAINER, f"{order_id}.json"
        )
        blob.upload_blob(
            json.dumps(order),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
        log.info("Order %s written to Blob Storage for store %s", order_id, order.get("storeId"))
        return jsonify({"orderId": order_id, "status": "Stored"}), 201

    log.error("Neither STORAGE_ACCOUNT_URL nor EVENTHUB_FQDN is set")
    return jsonify({"error": "The API isn't configured. Check the app settings."}), 500
