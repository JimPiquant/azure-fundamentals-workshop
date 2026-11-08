# Azure Fundamentals workshop: labs and lab code

This repository holds the labs and the code for the Azure Fundamentals workshop. You don't edit the code. Lab 2 tells you when to deploy each folder.

| Folder | What it is | Used in |
|---|---|---|
| `labs/` | The three lab guides in Markdown | Labs 1–3 |
| `order-api/` | A small Flask web API that accepts store orders (`POST /orders`). It saves each order to Blob Storage. When the Event Hubs settings exist, it sends each order to an event hub instead. | Lab 2, Part 1 and Part 2 |
| `order-functions/` | A Python Azure Function that runs when an event arrives, validates the order, and writes it to the `processed-orders` or `failed-orders` blob container. | Lab 2, Part 2 |

Neither app contains a key or a connection string. Both use a managed identity, so the labs grant that identity access to the resources that it needs.
