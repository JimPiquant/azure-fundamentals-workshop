# Lab 3: Observe and troubleshoot the order path

## Overview

In this lab, you operate the order API that you built in Lab 2, Part 1. You follow a valid order from the request to the stored blob, and then submit a request that breaks the API. You use the evidence in Azure Monitor to find where and why it failed, create an alert for failed requests, and resubmit the order safely. Finally, you delete the lab environment.

**Estimated time:** 45–60 minutes  
**Level:** 100–200  
**Primary interfaces:** Azure portal and Azure Cloud Shell (or your own Bash shell)

> 📝 **NOTE**
>
> This lab needs only Lab 2, Part 1. If you also completed the optional Part 2, the lab works too. Follow the notes in Task 2 and finish with the optional Task 5B.

## Architecture

```text
Command line (client)
   |  HTTPS POST /orders
   v
App Service web app (order API) --managed identity--> Blob container "orders"
   |
   |  telemetry
   v
Application Insights --> Log Analytics workspace
   |
   |  metric
   v
Alert rule --> Action group --> email
```

### How this lab maps to the module

| Step | What you do | Task |
|---|---|---|
| Explore | Open Application Insights, the web app metrics, and the Log Analytics workspace | 1 |
| Run | Submit a valid order and note its order ID | 2 |
| Trace | Follow the order from the request to the blob | 3 |
| Fail | Submit a request that breaks the API, and find the failure and its cause | 4 |
| Respond | Create an alert for failed requests, and resubmit the order safely | 5 |
| Extend (optional) | Follow an order through Event Hubs and the function (Lab 2, Part 2 only) | 5B |
| Clean up | Delete the lab resource group | 6 |

## Learning objectives

After completing this lab, you should be able to:

- Recognize which question metrics, logs, and traces each answer.
- Follow one business transaction through an API by using its order ID.
- Find a failed request and the exception behind it.
- Create an actionable metric alert.
- Explain why resubmitting an order is safe in this design.
- (Optional, with Lab 2 Part 2) Explain why a successful invocation isn't always a successful order.

## Prerequisites

You need:

- The environment from Lab 2, Part 1, with every resource still deployed and `PX-1001` stored in the `orders` container.
- The `<unique>` identifier that you chose in Lab 1.
- Your Bash command line from Lab 2 (Azure Cloud Shell, or your own Bash shell).

## Resource names

Replace `<unique>` with your identifier in every name before you select **Create**.

| Resource | Name | Task |
|---|---|---|
| Action group | `ag-orders-lab-<unique>` | 5 |
| Alert rule | `alert-orders-5xx-<unique>` | 5 |

> 📝 **NOTE**
>
> Telemetry can take a few minutes to appear. If a view is empty, wait, and then refresh it.

---

# Task 1: Explore the monitoring views

1. Open `appi-orders-<unique>`. On **Overview**, review the **Failed requests**, **Server response time**, and **Server requests** charts.
2. Under **Investigate**, select **Application map**. Identify the web app. If it's missing, it hasn't sent telemetry yet. Submit a request in Task 2, and then look again.
3. Open `app-orders-<unique>`. Under **Monitoring**, select **Metrics**. Add these Log-based metrics (use + Metric to add more than one metric to the chart):
   - Server requests
   - Failed requests
   - Server response time
4. Open `log-orders-<unique>` and select **Logs**. Close any query gallery that opens. Under **Tables**, find the Application Insights tables: `AppRequests`, `AppDependencies`, `AppTraces`, and `AppExceptions`. Note that you may have to select the "tables" icon next to the run button.

✅ **Checkpoint:** You can open each view and name the question it answers: metrics show how much and how often, logs show what happened, and traces show where it happened.

---

# Task 2: Run a valid order

1. Open your command line. If you opened a new session, your variables are gone. Load them, and then find the web app's address:

   ```bash
   source ~/lab.env # not needed if your terminal session is still active
   cd $LABDIR
   WEBAPP_HOST=$(az webapp show -g $RG -n $WEBAPP --query defaultHostName -o tsv)
   ORDERS_OUT=orders
   echo $WEBAPP_HOST
   ```

   The last command must print a host name that ends in `azurewebsites.net`. If it prints an empty line, check `$RG` and `$WEBAPP` with `echo $RG $WEBAPP`. If either is empty, `~/lab.env` wasn't loaded.

2. Submit an order, and note the time:

   ```bash
   curl -s -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '{"orderId":"PX-2001","storeId":"0412","items":[{"sku":"10045","quantity":12}]}'
   date -u
   ```

3. Record the order ID (`PX-2001`) and the time. The order ID is your correlation key for this transaction.

✅ **Checkpoint:** The response is `{"orderId":"PX-2001","status":"Stored"}`.

> 📝 **NOTE**
>
> If you completed Lab 2, Part 2, the response is `{"orderId":"PX-2001","status":"Accepted"}`, and the order is saved in the `processed-orders` container instead of `orders`. In that case, run `ORDERS_OUT=processed-orders` now. The commands in this lab use `$ORDERS_OUT` to find the right container, and you can follow the optional Task 5B at the end.

---

# Task 3: Trace the order

## 3.1 Find the transaction

1. Open `appi-orders-<unique>`. Under **Investigate**, select **Search**.
2. Set the time range to the last 30 minutes, and search for `PX-2001`.
3. Select a result to open the end-to-end transaction details. Identify the web app request and its log messages. If the call to Blob Storage appears as a dependency, identify it too.

## 3.2 Query by order ID

Application Insights doesn't record request bodies, so the order ID appears only in the API's log messages. The query first finds the operations whose log messages mention the order ID, and then returns every request, dependency, log message, and exception in those operations.

Note: We are using the Kusto Query Language (KQL) for this step. There is a toggle for **Simple mode** and **KQL mode** in the upper right.

1. In `appi-orders-<unique>`, under **Monitoring**, select **Logs**, and run:

   ```kusto
   let orderOps = union traces, exceptions
       | where timestamp > ago(30m)
       | where * has "PX-2001"
       | distinct operation_Id;
   union requests, dependencies, traces, exceptions
   | where timestamp > ago(30m)
   | where operation_Id in (orderOps)
   | project timestamp, itemType, cloud_RoleName, name, message, success, resultCode, operation_Id
   | order by timestamp asc
   ```

2. In `log-orders-<unique>`, select **Logs**, and run the same query against the workspace tables. Notice the different table and column names:

   ```kusto
   let orderOps = union AppTraces, AppExceptions
       | where TimeGenerated > ago(30m)
       | where * has "PX-2001"
       | distinct OperationId;
   union AppRequests, AppDependencies, AppTraces, AppExceptions
   | where TimeGenerated > ago(30m)
   | where OperationId in (orderOps)
   | project TimeGenerated, Type, AppRoleName, Name, Message, Success, ResultCode, OperationId
   | order by TimeGenerated asc
   ```

3. Confirm that the order file exists in storage:

   ```bash
   az storage blob list --account-name $STORAGE --container-name $ORDERS_OUT --prefix PX-2001 --auth-mode key --query "[].name" -o tsv
   ```

   The command must print `PX-2001.json`. If you completed Part 2 and it prints nothing, wait a minute for the function to process the order, and run it again.

✅ **Checkpoint:** You can list what happened to `PX-2001`: the request, the log message that names the order, and the stored blob.

💡 **Why this matters:** One query by order ID answers "what happened to this order?" without opening each service. That only works because the API writes the order ID into its log messages.

---

# Task 4: Cause and investigate a controlled failure

A client that sends a list of orders instead of a single order is a realistic mistake. The API expects one order, so it fails.

1. Submit the batch:

   ```bash
   curl -s -w "\nHTTP %{http_code}\n" -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '[{"orderId":"PX-2002","storeId":"0412","items":[{"sku":"10045","quantity":6}]}]'
   ```

   The last line is `HTTP 500`. The client knows that the order wasn't accepted.

2. Wait one to two minutes. In `appi-orders-<unique>`, under **Investigate**, select **Failures**. Find the failed `POST /orders` request, and then select the exception to read its details.
3. In **Logs**, run:

   ```kusto
   union requests, exceptions
   | where timestamp > ago(30m)
   | where (itemType == "request" and success == false) or itemType == "exception"
   | project timestamp, itemType, cloud_RoleName, name, resultCode, type, outerMessage, operation_Id
   | order by timestamp asc
   ```

   Look for a `POST /orders` request with `resultCode` 500, and an exception whose message says that a `list` object has no attribute `get`. The exception shows what the code tried to do with the list.

4. Search `appi-orders-<unique>` for `PX-2002`. Notice that nothing names the order. The API writes the order ID to its log only after the order is stored, so you identify this failure by its time and its 500 status.
5. In the `app-orders-<unique>` **Metrics** view from Task 1, confirm that **Http 5xx** increased.
6. Confirm that the order wasn't stored:

   ```bash
   az storage blob list --account-name $STORAGE --container-name $ORDERS_OUT --prefix PX-2002 --auth-mode key --query "[].name" -o tsv
   ```

   The command must print nothing.

✅ **Checkpoint:** You can show where `PX-2002` failed (the API, on a list payload), what evidence exists (a 500 request, an exception, and an Http 5xx metric increase), and that no order file was written.

💡 **Why this matters:** The failed request doesn't name the order, because the API logs the order ID only on success. In production, log the order ID when the request arrives, so that a failure points to the order that needs attention.

---

# Task 5: Respond

## 5.1 Create a failed-request alert

1. Open `app-orders-<unique>`. Under **Monitoring**, select **Alerts** > **+ Create** > **Alert rule**.
2. On the **Condition** tab, select the signal **Failed requests**, and configure:
   - **Aggregation type:** Count
   - **Operator:** Greater than
   - **Threshold value:** 0
   - **Check every:** 1 minute
   - **Lookback period:** 5 minutes
3. On the **Actions** tab, select **Create action group**:
   - On **Basics**, select your resource group, enter `ag-orders-lab-<unique>` as the **Action group name**, and enter `orders-lab` as the **Display name** (12 characters or fewer).
   - On **Notifications**, select **Email/SMS message/Push/Voice**, select **Email**, enter your own email address, and name the notification `email-me`.
   - Select **Review + create** > **Create**.
4. Wait a few minutes and check your email. Respond to any email validation requests.
4. On the **Details** tab, set **Severity** to **2 - Warning**, enter `alert-orders-5xx-<unique>` as the name, and then select **Review + create** > **Create**.
5. Submit another batch, so that the alert has a new failure to detect:

   ```bash
   curl -s -w "\nHTTP %{http_code}\n" -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '[{"orderId":"PX-2003","storeId":"0412","items":[{"sku":"10045","quantity":3}]}]'
   ```

6. Continue with 5.2. You check the alert at the end of this task.

**Discussion:** Is this alert actionable? Who should receive it, and what should they do first?

> 📝 **NOTE**
>
> A metric alert watches only the count of failed requests. It can't tell you which order failed or why. That's what the logs are for. The alert tells you when to look.

## 5.2 Decide how to resubmit safely

Discuss these questions with your group:

- Is the failure transient or a data problem? A list payload is a data problem, so sending the same request again won't help.
- Where should the fix happen: in the client, or in the API?
- Why is resubmitting safe here? The API writes `<orderId>.json`, so storing the same order twice overwrites one file instead of creating a duplicate.

Then resubmit both orders, each as a single order:

```bash
curl -s -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '{"orderId":"PX-2002","storeId":"0412","items":[{"sku":"10045","quantity":6}]}'
curl -s -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '{"orderId":"PX-2003","storeId":"0412","items":[{"sku":"10045","quantity":3}]}'
```

Confirm that both files now exist:

```bash
az storage blob list --account-name $STORAGE --container-name $ORDERS_OUT --prefix PX-200 --auth-mode key --query "[].name" -o tsv
```

The command must print `PX-2001.json`, `PX-2002.json`, and `PX-2003.json`. If you completed Part 2, wait a minute and run it again.

## 5.3 Check the alert

1. In the portal, search for **Monitor**, select it, and then select **Alerts**.
2. Within about five to ten minutes, an alert for `alert-orders-5xx-<unique>` appears in the list. If an email notification is set up, you also receive an email.

✅ **Checkpoint:** The alert rule exists, and the corrected `PX-2002` and `PX-2003` orders are stored. An alert from the earlier failures appears under **Alerts** (this can take several minutes).

---

# Task 5B (optional): Follow an order through Event Hubs and the function

Do this task only if you completed Lab 2, Part 2. Otherwise, go to Task 6.

1. Open `evh-orders-<unique>`. Under **Monitoring**, select **Metrics**. Set the time range to the last 30 minutes, and add **Incoming Messages**, **Outgoing Messages**, and **Throttled Requests**. Both message counts rise for each order. If incoming messages rise and outgoing messages don't, the function isn't reading the events.
2. In `appi-orders-<unique>` > **Logs**, run the Task 3.2 query again for `PX-2001`. The results now include the web app's message `Order PX-2001 sent to Event Hubs`, and the function's messages `Processing order PX-2001` and `Order PX-2001 written to processed-orders`. The function run can appear under a different `operation_Id` than the web request, so use the order ID to connect them.
3. Submit an order with an invalid quantity:

   ```bash
   curl -s -X POST "https://$WEBAPP_HOST/orders" -H "Content-Type: application/json" -d '{"orderId":"PX-2004","storeId":"0412","items":[{"sku":"10045","quantity":0}]}'
   ```

   The API returns `Accepted`, because the API doesn't validate orders. The function does.
4. Wait one to two minutes, and then run this query:

   ```kusto
   union traces, exceptions
   | where timestamp > ago(30m)
   | where * has "PX-2004"
   | project timestamp, itemType, cloud_RoleName, severityLevel, message, operation_Id
   | order by timestamp asc
   ```

   Look for the function's warning `Order PX-2004 failed validation: every item needs a quantity greater than 0`. No exception appears, because the function handled the problem on purpose.
5. Read the failed order, and confirm that it wasn't processed:

   ```bash
   az storage blob download --account-name $STORAGE --container-name failed-orders --name PX-2004.json --auth-mode key --file PX-2004.json -o none && cat PX-2004.json
   az storage blob list --account-name $STORAGE --container-name processed-orders --prefix PX-2004 --auth-mode key --query "[].name" -o tsv
   ```

   The first command prints the order and the reason. The second prints nothing.
6. Open `func-orders-<unique>`, select `process_order`, and then select **Invocations**. The run for `PX-2004` is marked as a success, because the function didn't throw an error.

✅ **Checkpoint:** You can show the validation warning and the `failed-orders` blob for `PX-2004`, and explain why the Event Hubs metrics and the function invocation both look healthy.

💡 **Why this matters:** A delivered event and a successful invocation show that the pipeline worked, not that the business result is right. Event Hubs has no dead-letter queue, so the `failed-orders` container is where an invalid order waits for someone to review it. Decide who owns that review.

---

# Task 6: Clean up

Deleting the resource group removes every resource from Labs 2 and 3, including the alert rule and the action group.

1. In the portal search box, enter **Resource groups**, and then select **Resource groups**.
2. Select `rg-orders-lab-<unique>`, and confirm that it contains only your lab resources.
3. Select **Delete resource group**, enter the resource-group name, and confirm.
4. Return to **Resource groups**, and verify that the resource group is being deleted or no longer appears.

> ⚠️ **WARNING**
>
> Resource-group deletion is irreversible. Verify the resource-group name before confirming. Cost reporting can lag behind deletion.

✅ **Final checkpoint:** The lab resource group and its resources have been deleted.

---

# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| A view or query returns nothing | Telemetry takes a few minutes to arrive, or the time range is too short | Wait two to three minutes, widen the time range, and refresh. |
| The Task 3 query returns nothing for `PX-2001` | The API's log messages aren't in the `traces` table | Run the next row's query instead, and match the request by its time. |
| You need the request without the order ID | The log message wasn't captured | Run `requests \| where timestamp > ago(30m) \| where name has "orders" \| project timestamp, name, resultCode, success, operation_Id \| order by timestamp desc` in `appi-orders-<unique>`. |
| Failures shows the 500 request but no exception | Exception telemetry isn't captured for this app | Turn on the web app's log stream with `az webapp log config -g $RG -n $WEBAPP --docker-container-logging filesystem`, repeat the failing request, and then run `az webapp log tail -g $RG -n $WEBAPP`. |
| `curl` returns `HTTP 500` for a valid single order | The API or its role is broken, not the request | Go back to Lab 2, Part 1 and check the web app's settings and its **Storage Blob Data Contributor** role. |
| `$WEBAPP_HOST` or `$ORDERS_OUT` is empty | A new shell session lost the variables | Run `source ~/lab.env`, and then repeat the variable commands from Task 2. |
| The alert doesn't appear | Alerts evaluate on a schedule, and the lookback is five minutes | Wait ten minutes. In the web app's **Metrics** view, confirm that **Http 5xx** shows a value greater than 0 for that time. |

---

# Knowledge check

1. Which signal showed the failure first, and which one told you why it failed?
2. Why couldn't you find `PX-2002` in the telemetry, and what would you change in the API?
3. Is the failure transient or a data problem, and what does that mean for retrying?
4. Why is resubmitting `PX-2002` safe in this design?
5. When do you query the `requests` table, and when do you query `AppRequests`?
6. Is the **Http 5xx** alert actionable? Who should receive it, and what should they do first?

# Reference links

- [Application Insights overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [Investigate failures, performance, and transactions with Application Insights](https://learn.microsoft.com/en-us/azure/azure-monitor/app/failures-performance-transactions)
- [Application Insights telemetry data model](https://learn.microsoft.com/en-us/azure/azure-monitor/app/data-model-complete)
- [Overview of Log Analytics in Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-overview)
- [Monitor Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/monitor-app-service)
- [Enable diagnostic logging for apps in Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/troubleshoot-diagnostic-logs)
- [Create Azure Monitor metric alert rules](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-create-metric-alert-rule)
- [Create and manage action groups](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/action-groups)
- [Delete resource groups and resources](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group)
