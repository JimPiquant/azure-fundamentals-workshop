# Lab 2: Build an order path

## Overview

In this lab, you build the order path used for the rest of the day.

- **Part 1 (required):** A web API hosted in Azure App Service accepts store orders and writes each one to Azure Blob Storage.
- **Part 2 (optional):** You put Azure Event Hubs between the API and storage. The API sends each order to an event hub, and a function on the Azure Functions Flex Consumption plan picks it up, validates it, and writes it to Blob Storage.

Both apps use managed identities, so no keys or connection strings are stored in their configuration, and both send telemetry to one Application Insights resource.

You don't write code. You clone a repository that holds two small apps, and you deploy them from Azure Cloud Shell.

**Estimated time:** Part 1, 45–60 minutes. Part 2, 60–75 minutes.  
**Level:** 100–200  
**Primary interfaces:** Azure portal and a Bash command line (Azure Cloud Shell, or your own Bash shell)

> ❗ **IMPORTANT**
>
> Keep every resource you create in this lab. Lab 3 uses the same environment and ends with cleanup.

## Architecture

**Part 1**

```text
Command line (client)
   |  HTTPS POST /orders
   v
App Service web app (order API) --managed identity--> Blob container "orders"

Application Insights <-- telemetry from the web app
```

**Part 2**

```text
Command line (client)
   |  HTTPS POST /orders
   v
App Service web app (order API) --managed identity--> Event hub "orders"
                                                            |  trigger
                                                            v
        Function app (Flex Consumption) --managed identity--> Blob containers
                                                              "processed-orders"
                                                              "failed-orders"

Application Insights <-- telemetry from both apps
```

### How this lab maps to the module

| Building block | Service in this lab | Why it fits | Part |
|---|---|---|---|
| Host | App Service web app | A continuously available HTTP API | 1 |
| Store objects | Blob Storage | Each order is saved as a JSON object | 1 |
| Observe | Application Insights | One place to follow an order | 1 |
| Communicate | Event Hubs | A high-volume stream of events that several consumers can read independently | 2 |
| Execute | Azure Functions (Flex Consumption) | Event-driven code that runs only when events arrive | 2 |

## Learning objectives

After completing Part 1, you should be able to:

- Use Azure Cloud Shell, or a local Bash shell, to run Azure CLI commands.
- Create a storage account and an App Service web app.
- Turn on a system-assigned managed identity and grant it a data-plane role at the narrowest practical scope.
- Deploy code from a Git repository to App Service and confirm that an order is stored.

After completing Part 2, you should also be able to:

- Create an Event Hubs namespace and event hub, and explain why the API hands orders to an event stream instead of processing them directly.
- Explain when App Service and Azure Functions each fit.
- Configure identity-based connections that name a resource instead of storing a secret.
- Confirm that an order flows end to end.

## Prerequisites

You need:

- Access to the [Azure portal](https://portal.azure.com/).
- The Azure subscription that you used in Lab 1. You own it, so you can create resources and role assignments.
- The `<unique>` identifier that you chose in Lab 1.
- A Bash command line. The next section describes your two options.
- Internet access to clone the lab repository from GitHub. The repository is public, so you don't need a GitHub account.

> ❗ **IMPORTANT**
>
> Use the names, **Central US**, and the pricing tiers in this lab. The App Service plan and Event Hubs namespace incur charges while they exist, so don't skip the cleanup in Lab 3.

## Before you start: pre-flight check

1. In the Azure portal, open your subscription, and then select **Settings** > **Resource providers**.
2. Confirm that each of these providers is **Registered**. Select **Register** for any that aren't, and wait for the status to change.
   - `Microsoft.Web`
   - `Microsoft.Storage`
   - `Microsoft.Insights`
   - `Microsoft.OperationalInsights`
   - `Microsoft.EventHub` (Part 2)
   - `Microsoft.App` (Part 2)

---

# Get ready: set up your command line and the lab code

You run the deployment and verification commands in a Bash shell. Choose **one** of the two options.

## Option A: Azure Cloud Shell (recommended)

Cloud Shell is a Bash shell that runs in your browser. It already has the Azure CLI, Git, and `zip`, and it is already signed in, so you don't install anything.

1. In the Azure portal, select the **Cloud Shell** icon (**>_**) in the top toolbar.
2. When asked to choose a shell, select **Bash**.
3. The first time you start Cloud Shell, it asks about storage:
   - Select **Mount storage account**, choose your subscription, and then select **Apply** and let Azure create the storage account for you.
   - A persistent home folder keeps the files that you download, so you don't lose them. The storage costs only a few cents per month. It is in its own resource group, so deleting `rg-orders-lab-<unique>` in Lab 3 doesn't remove it. You can delete it after the workshop.
4. Verify that you're in the right subscription:

   ```bash
   az account show --query "{subscription:name, tenant:tenantId}" -o table
   ```

   If it shows the wrong subscription, run `az account set --subscription "<your subscription name>"`. If you belong to more than one directory, use **Settings** > **Directories + subscriptions** in the portal to switch to your personal directory, and then reopen Cloud Shell.

**Tips for using Cloud Shell**

- **Paste:** Use **Ctrl+Shift+V** (**Cmd+V** on a Mac). Right-click also offers **Paste**.
- **Multi-line commands:** Commands that end a line with `\` continue on the next line. If a paste fails, paste the command as one line without the `\`.
- **Timeout:** Cloud Shell ends after about 20 minutes with no activity. Your files remain, but your variables don't. After you reconnect, run `source ~/lab.env` and `cd $LABDIR` (you create both below).
- **Edit a file:** Enter `code <file name>` to open the built-in editor.

## Option B: Your own Bash shell

Use this option only if you prefer to work on your own computer. Your computer needs:

| Requirement | Notes |
|---|---|
| **Bash** | Linux or macOS. On Windows, use **WSL 2** with Ubuntu. Git Bash and PowerShell aren't supported. |
| **Azure CLI** | A current version. Check with `az version`, and update with `az upgrade`. See [Install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli). |
| **Git** | Check with `git --version`. |
| **zip** | Check with `zip -v`. On Ubuntu, install it with `sudo apt install zip`. |
| **curl** | Check with `curl --version`. |
| **Internet access** | To reach GitHub, the Azure portal, and your Azure resources. |

You don't need Python, Node.js, or an editor. Azure builds the apps for you.

Sign in and select your subscription:

```bash
az login
az account set --subscription "<your subscription name>"
az account show --query "{subscription:name, tenant:tenantId}" -o table
```

If the browser can't open (for example, in WSL), use `az login --use-device-code` and follow the instructions on screen. Sign in with the account for your personal tenant, and confirm that the subscription shown is the one you use for this workshop.

## Save your names and clone the lab code

Run these steps once, in the shell you chose.

1. Replace `jw482` with your own identifier from Lab 1, and then run the command. It saves your resource names in a file so that you can reload them at any time.

   ```bash
   UNIQUE=jw482
   cat > ~/lab.env <<EOF
   export UNIQUE=$UNIQUE
   export RG=rg-orders-lab-$UNIQUE
   export STORAGE=storders$UNIQUE
   export EH_NS=evh-orders-$UNIQUE
   export WEBAPP=app-orders-$UNIQUE
   export FUNCAPP=func-orders-$UNIQUE
   EOF
   source ~/lab.env
   echo "Resource group: $RG"
   ```

   The output must show your identifier, for example `rg-orders-lab-jw482`.

2. Clone the lab repository, and then open it.

   ```bash
   git clone https://github.com/JimPiquant/azure-fundamentals-workshop.git
   cd azure-fundamentals-workshop
   echo "export LABDIR=$(pwd)" >> ~/lab.env
   ls
   ```

   ✅ **Checkpoint:** The `ls` output lists the `labs`, `order-api` and `order-functions` folders.

> 📝 **NOTE**
>
> If you reconnect to your shell later, run `source ~/lab.env` and `cd $LABDIR` before you continue.

✅ **Checkpoint:** `echo $RG` prints your resource group name, and `ls $LABDIR` lists `labs`, `order-api` and `order-functions`.

## Resource names

Replace `<unique>` in portal steps with the identifier that you chose in Lab 1: your initials plus three digits, in lowercase letters and numbers only (for example, `jw482`).

| Resource | Suggested name | Part |
|---|---|---|
| Resource group | `rg-orders-lab-<unique>` | 1 |
| Log Analytics workspace | `log-orders-<unique>` | 1 |
| Application Insights | `appi-orders-<unique>` | 1 |
| Storage account (order data) | `storders<unique>` | 1 |
| Blob container (received orders) | `orders` | 1 |
| App Service plan | `asp-orders-<unique>` | 1 |
| Web app | `app-orders-<unique>` | 1 |
| Event Hubs namespace | `evh-orders-<unique>` | 2 |
| Event hub | `orders` | 2 |
| Blob containers (function output) | `processed-orders`, `failed-orders` | 2 |
| Function app | `func-orders-<unique>` | 2 |

Storage account, web app, function app, and Event Hubs namespace names must be globally unique. Storage-account names must be 3–24 characters long and contain only lowercase letters and numbers.

---

# Part 1: Host an order API that stores orders in Blob Storage

## Task 1: Create the resource group and monitoring resources

1. Create a resource group named `rg-orders-lab-<unique>` in **Central US**, with the tag `environment` = `development`.
2. In the portal search box, enter **Log Analytics workspaces**, select it, and then select **Create**. Select your resource group, enter `log-orders-<unique>`, select **Central US**, and then select **Review + create** > **Create**.
3. In the portal search box, enter **Application Insights**, select it, and then select **Create**. Select your resource group, enter `appi-orders-<unique>`, select **Central US**, and for **Log Analytics workspace** select `log-orders-<unique>`. Select **Review + create** > **Create**.

✅ **Checkpoint:** The resource group contains a Log Analytics workspace and an Application Insights resource.

💡 **Why this matters:** Every app in this lab sends telemetry to the same Application Insights resource, so in Lab 3 you can follow one order across all of them.

---

## Task 2: Create the storage account and container

1. Create a storage account named `storders<unique>` in your resource group and in `Central US`. Use Primary Service `Azure Blob Storage or Azure Data Lake Storage`, `General purpose` as the primary workload and `Locally-redundant storage (LRS)`, and keep the other defaults.
2. When deployment completes, open the storage account. Under **Data storage**, select **Containers** > **+ Add container**.
3. Enter `orders`, leave **Anonymous access level** set to **Private (no anonymous access)**, and select **Create**.

✅ **Checkpoint:** The `orders` container exists and the `Anonymouse access level` is private.

---

## Task 3: Create the web app

1. In the portal search box, enter **App Services**, select it, and then select **Create** > **Web App**.
2. On the **Basics** tab, configure:
   - **Resource group:** `rg-orders-lab-<unique>`
   - **Name:** `app-orders-<unique>`
   - **Publish:** Code
   - **Runtime stack:** Python 3.12
   - **Operating System:** Linux
   - **Region:** **Central US**
   - **Linux Plan:** create a new plan named `asp-orders-<unique>`
   - **Pricing plan:** Basic B1
3. On the **Monitoring** tab, set **Enable Application Insights** to **Yes**, and select `appi-orders-<unique>`.
4. Keep the defaults on the remaining tabs, and then select **Review + create** > **Create**.

✅ **Checkpoint:** The web app and its App Service plan exist, and the web app is connected to `appi-orders-<unique>`.

---

## Task 4: Turn on the web app's identity and let it write orders

### 4.1 Turn on the identity

1. Open `app-orders-<unique>`. Under **Settings**, select **Identity**. On the **System assigned** tab, set **Status** to **On**, select **Save**, and confirm.
2. Verify the identity in your shell. The command must print a value (an object ID). If it prints nothing, the identity isn't on yet.

   ```bash
   az webapp identity show -g $RG -n $WEBAPP --query principalId -o tsv
   ```
✅ **Checkpoint:** The command must print an object ID (a guid).

### 4.2 Grant the role on the container

1. Open the storage account `storders<unique>`. Under **Data storage**, select **Containers**, and then select the `orders` container.
2. Select **Access control (IAM)** > **+ Add** > **Add role assignment**.
3. Select **Storage Blob Data Contributor**, and then select **Next**.
4. For **Assign access to**, select **Managed identity**. Select **+ Select members**, set **Managed identity** to **App Service**, select `app-orders-<unique>`, and then select **Select**.
5. Select **Review + assign** twice.

| Principal | Role | Scope |
|---|---|---|
| `app-orders-<unique>` | Storage Blob Data Contributor | `orders` container |

> 📝 **NOTE**
>
> Role assignments can take several minutes to propagate. Scoping the role to one container, rather than the storage account, applies least privilege.

✅ **Checkpoint:** The role assignment appears under **Access control (IAM)** > **Role assignments** on the `orders` container.

---

## Task 5: Add the web app settings

1. Go to `App Services` and open `app-orders-<unique>`. Under **Settings**, select **Environment variables**.
2. On the **App settings** tab, add these settings, and then select **Apply** and confirm:

   | Name | Value |
   |---|---|
   | `STORAGE_ACCOUNT_URL` | `https://storders<unique>.blob.core.windows.net` |
   | `ORDERS_CONTAINER` | `orders` |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |

> ❗ **IMPORTANT**
>
> Replace `<unique>` with your own identifier in every value, for example `https://storders<unique>.blob.core.windows.net` becomes `https://stordersjw482.blob.core.windows.net`. Azure doesn't reject a value that still contains `<unique>`, so the app fails later without a clear error.

3. Verify the settings in your shell. Confirm that no value contains `<` or `>`.

   ```bash
   az webapp config appsettings list -g $RG -n $WEBAPP --query "[?name=='STORAGE_ACCOUNT_URL' || name=='ORDERS_CONTAINER' || name=='SCM_DO_BUILD_DURING_DEPLOYMENT'].{name:name,value:value}" -o table
   ```

💡 **Why this matters:** The setting names a resource. The app's managed identity provides the proof of who is calling, so the value isn't a secret.

✅ **Checkpoint:** The web app lists the three settings, and the two that you verified contain your identifier.

---

## Task 6: Deploy the order API

1. In your shell, go to the lab folder and package the order API. App Service needs `app.py` at the top level of the zip, so run `zip` from inside the `order-api` folder.

   ```bash
   cd $LABDIR/order-api
   zip -r ../order-api.zip . -x '*__pycache__*'
   cd $LABDIR
   ```

2. Deploy the package to the web app:

   ```bash
   az webapp deploy --resource-group $RG --name $WEBAPP --src-path ./order-api.zip --type zip
   ```

   The command can take a few minutes, because App Service installs the Python packages that `requirements.txt` lists.

3. Check that the API responds:

   ```bash
   WEBAPP_HOST=$(az webapp show -g $RG -n $WEBAPP --query defaultHostName -o tsv)
   curl -s "https://$WEBAPP_HOST/"
   ```

   The expected response is `Order API is running (orders go to Blob Storage)`. The first request after a deployment can take up to a minute while the app starts.

✅ **Checkpoint:** The health check returns `Order API is running (orders go to Blob Storage)`.

---

## Task 7: Submit an order and view it

1. Submit an order:

   ```bash
   curl -s -X POST "https://$WEBAPP_HOST/orders" \
     -H "Content-Type: application/json" \
     -d '{"orderId":"PX-1001","storeId":"0412","items":[{"sku":"10045","quantity":24}]}'
   ```

   The expected response is `{"orderId":"PX-1001","status":"Stored"}`. If you receive an error within a few minutes of the role assignment, wait and try again.

2. List the blobs in the `orders` container, and then show the order:

   ```bash
   az storage blob list --account-name $STORAGE --container-name orders --auth-mode key --query "[].name" -o tsv
   az storage blob download --account-name $STORAGE --container-name orders --name PX-1001.json --auth-mode key --file PX-1001.json -o none && cat PX-1001.json
   ```

   The file contains your order and `"status": "Received"`. You use `--auth-mode key` so that the command works without a data role for your own account. The web app didn't use a key. It used its managed identity.

3. In the portal, open `storders<unique>` > **Containers** > `orders`. If the portal says that you don't have permission to list blobs, select **Switch to Access key** in the message, or choose **Authentication method** > **Access key**.

> 📝 **NOTE**
>
> If `curl` returns an error after several minutes, use the troubleshooting table below.

## Troubleshooting Part 1

| Symptom | Likely cause | Fix |
|---|---|---|
| The health check returns nothing, or an error page, for several minutes | The app is still starting, or the packages didn't install | Wait a minute and retry. Confirm that `SCM_DO_BUILD_DURING_DEPLOYMENT` is `true` (Task 5), and run the deployment in Task 6 again. |
| The health check says `Order API is running (orders go to Event Hubs)` | The Part 2 settings are already present | This is expected after Part 2. |
| `curl` returns 500 and `The API isn't configured` | `STORAGE_ACCOUNT_URL` is missing | Add or correct the setting (Task 5), and then retry. |
| `curl` returns 500 with no message | The identity or the role is missing, or the setting still contains `<unique>` | Check the identity (4.1), the role on the `orders` container (4.2), and the settings (Task 5). Wait a few minutes after assigning the role. |

✅ **Checkpoint:** `PX-1001.json` exists in the `orders` container and contains `"status": "Received"`.

## Part 1 knowledge check

1. Which identity wrote the order to the container? Which role gave it permission, and at which scope?
2. What does `STORAGE_ACCOUNT_URL` contain, and why isn't it a secret?
3. What would happen to an order if the storage account were briefly unavailable when the API tried to save it? What does that suggest about putting a buffer, such as an event hub, between the API and storage?

**Part 1 is complete.** If you have time, continue with Part 2. Otherwise, go to **Cleanup**.

---

# Part 2 (optional): Process orders with Event Hubs and Azure Functions

In Part 2, you change the order flow path. The web app sends each order to an event hub instead of writing it to storage, and a function app picks up the event and writes the result. Adding two settings to the web app switches on this behavior. You don't redeploy the API.  See the source code in the repo if you are curious.

## Task 8: Create the Event Hubs namespace and event hub

1. In the portal search box, enter **Event Hubs**, select it, and then select **+ Create**.
2. On the **Basics** tab, configure:
   - **Resource group:** `rg-orders-lab-<unique>`
   - **Namespace name:** `evh-orders-<unique>`
   - **Location:** **Central US**
   - **Pricing tier:** Standard
   - **Throughput Units:** 1
3. Select **Review + create**, and then select **Create**. When deployment completes, select **Go to resource**.
4. Under **Entities**, select **Event Hubs**, and then select **+ Event Hub**.
5. Enter `orders` as the name, leave the other settings at their defaults, and select **Review + create** > **Create**.

> 📝 **NOTE**
>
> An event hub keeps a stream of events for a retention period, and each consumer reads at its own pace. Unlike a queue, it doesn't track which individual event was handled, and it has no dead-letter queue. The function records its place in the stream with a checkpoint.

✅ **Checkpoint:** The `orders` event hub exists in `evh-orders-<unique>`.

---

## Task 9: Create the output containers

1. Open the storage account `storders<unique>`. Under **Data storage**, select **Containers**.
2. Create two private containers: `processed-orders` and `failed-orders`.

✅ **Checkpoint:** The storage account has the containers `orders`, `processed-orders`, and `failed-orders`.

---

## Task 10: Create the function app

1. In the portal search box, enter **Function App**, select it, and then select **Create**.
2. Select the **Flex Consumption** hosting option, and then select **Select**.
3. On the **Basics** tab, configure:
   - **Resource group:** `rg-orders-lab-<unique>`
   - **Function App name:** `func-orders-<unique>`
   - **Region:** **Central US**
   - **Runtime stack:** Python
   - **Version:** 3.12
   - **Instance size:** keep the default
4. On the **Storage** tab, keep the defaults. The portal creates a storage account for the function app's own use (`storders<unique>` holds order data, so don't select it here).
5. On the **Monitoring** tab, set **Enable Application Insights** to **Yes**, and select `appi-orders-<unique>`.
6. On the **Authentication** tab, set **Authentication type** to **Managed identity** for all three resources: host storage, deployment storage, and Application Insights. Set the identity type to **System assigned**.
7. Keep the defaults on the remaining tabs, and then select **Review + create** > **Create**.

> ❗ **IMPORTANT**
>
> Don't skip step 6. The default authentication type uses a storage connection string, which puts a key in an app setting. Managed identity removes the key, and the portal assigns the roles that the function app needs on its own storage account.

> 📝 **NOTE**
>
> If you choose **User assigned** instead, the portal creates an identity named `func-orders-<unique>-uami`. This lab doesn't use it. Never assign roles to it in Task 11.

8. After the deployment finishes, verify that the function app uses identity-based storage. The command must list names that end in `__credential` (for example `AzureWebJobsStorage__credential`). If it lists a plain `AzureWebJobsStorage` setting, the app uses a connection string. Delete the function app and create it again with step 6.

   ```bash
   az functionapp config appsettings list -g $RG -n $FUNCAPP --query "[?starts_with(name,'AzureWebJobsStorage')].name" -o tsv
   ```

✅ **Checkpoint:** The function app exists on the Flex Consumption plan, is connected to `appi-orders-<unique>`, and uses managed identity for its storage.

---

## Task 11: Turn on the function's identity and grant data roles

### 11.1 Check the function's identity

1. Open `func-orders-<unique>`. Under **Settings**, select **Identity**. On the **System assigned** tab (not **User assigned**), **Status** should already be **On** because of Task 10 step 6. If it's **Off**, set it to **On**, select **Save**, and confirm.
2. Verify the identity in your shell. The command must print a value (an object ID). If it prints nothing, the function app has no system-assigned identity yet.

   ```bash
   az functionapp identity show -g $RG -n $FUNCAPP --query principalId -o tsv
   ```

> ❗ **IMPORTANT**
>
> If the function app also has a user-assigned identity named `func-orders-<unique>-uami`, don't assign roles to it. In the next sections, always choose the **system-assigned** identity of `func-orders-<unique>`.

### 11.2 Let the web app send events

1. Open the Event Hubs namespace, select **Event Hubs**, and then select the `orders` event hub.
2. Select **Access control (IAM)** > **+ Add** > **Add role assignment**.
3. Select **Azure Event Hubs Data Sender**, and then select **Next**.
4. For **Assign access to**, select **Managed identity**. Select **+ Select members**, set **Managed identity** to **App Service**, select `app-orders-<unique>`, and then select **Select**.
5. Select **Review + assign** twice.

### 11.3 Let the function receive events

Repeat the steps in 11.2 on the same `orders` event hub, with these changes:

- **Role:** Azure Event Hubs Data Receiver
- **Managed identity:** Function App > `func-orders-<unique>`. If `func-orders-<unique>` isn't listed, the system-assigned identity isn't on. Return to 11.1. Don't select the `-uami` identity.

### 11.4 Let the function write order files

1. Open the storage account `storders<unique>`, and then select **Access control (IAM)** > **+ Add** > **Add role assignment**.
2. Assign **Storage Blob Data Contributor** to the system-assigned managed identity of `func-orders-<unique>` (**Managed identity** > **Function App**).

Here is what should now be in place:

| Principal | Role | Scope |
|---|---|---|
| `app-orders-<unique>` | Storage Blob Data Contributor | `orders` container (Part 1) |
| `app-orders-<unique>` | Azure Event Hubs Data Sender | `orders` event hub |
| `func-orders-<unique>` | Azure Event Hubs Data Receiver | `orders` event hub |
| `func-orders-<unique>` | Storage Blob Data Contributor | `storders<unique>` storage account |

> 📝 **NOTE**
>
> Role assignments can take several minutes to propagate. Scoping the Event Hubs roles to the event hub, rather than the namespace, applies least privilege.

✅ **Checkpoint:** The three new role assignments appear under **Access control (IAM)** > **Role assignments** on their scopes.

---

## Task 12: Add the identity-based connection settings

### 12.1 Web app settings

1. Open `app-orders-<unique>`. Under **Settings**, select **Environment variables**.
2. On the **App settings** tab, add these settings, and then select **Apply** and confirm:

   | Name | Value |
   |---|---|
   | `EVENTHUB_FQDN` | `evh-orders-<unique>.servicebus.windows.net` |
   | `EVENTHUB_NAME` | `orders` |

   The Event Hubs host name ends in `servicebus.windows.net`. That is correct.

   Selecting **Apply** restarts the web app. From now on, the API sends orders to the event hub instead of writing them to the `orders` container.

### 12.2 Function app settings

1. Open `func-orders-<unique>`. Under **Settings**, select **Environment variables**.
2. Add these settings, and then select **Apply** and confirm. Note the double underscore (`__`) in the first name.

   | Name | Value |
   |---|---|
   | `EventHubConnection__fullyQualifiedNamespace` | `evh-orders-<unique>.servicebus.windows.net` |
   | `ORDERS_STORAGE_URL` | `https://storders<unique>.blob.core.windows.net` |

> ❗ **IMPORTANT**
>
> Replace `<unique>` with your own identifier in every value, for example `evh-orders-jw482.servicebus.windows.net`. The Event Hubs value must not start with `https://` and must not contain spaces. Azure doesn't reject a value that still contains `<unique>`, so the function fails later without a clear error.

3. Verify the settings in your shell. Confirm that no value contains `<` or `>`.

   ```bash
   az webapp config appsettings list -g $RG -n $WEBAPP --query "[?contains(name,'EVENTHUB')].{name:name,value:value}" -o table
   az functionapp config appsettings list -g $RG -n $FUNCAPP --query "[?contains(name,'EventHub') || name=='ORDERS_STORAGE_URL'].{name:name,value:value}" -o table
   ```

💡 **Why this matters:** `EventHubConnection__fullyQualifiedNamespace` tells the Functions runtime which Event Hubs namespace to use. The function's managed identity provides the proof of who is calling, and none of these values is a secret. The Application Insights settings were added automatically when you enabled Application Insights.

✅ **Checkpoint:** Both apps show the new settings, with your identifier in every value.

---

## Task 13: Deploy the function

1. In your shell, package the function. The zip must hold `function_app.py` at its top level.

   ```bash
   cd $LABDIR/order-functions
   zip -r ../order-functions.zip . -x '*__pycache__*'
   cd $LABDIR
   ```

2. Deploy the package:

   ```bash
   az functionapp deployment source config-zip --resource-group $RG --name $FUNCAPP --src ./order-functions.zip --build-remote true
   ```

   The command can take a few minutes, because Azure installs the Python packages that `requirements.txt` lists. The `--build-remote true` option tells Azure to do that on its side.

3. Restart the function app so that it picks up the roles, settings, and code, and then confirm that the function is indexed:

   ```bash
   az functionapp restart -g $RG -n $FUNCAPP
   az functionapp function list -g $RG -n $FUNCAPP --query "[].{name:name,disabled:isDisabled}" -o table
   ```

   The function can take a minute or two to appear after the deployment finishes.

✅ **Checkpoint:** The function app lists `process_order` as not disabled.

---

## Task 14: Submit an order and follow it

1. Check that the API now uses Event Hubs, and then submit an order:

   ```bash
   curl -s "https://$WEBAPP_HOST/"
   curl -s -X POST "https://$WEBAPP_HOST/orders" \
     -H "Content-Type: application/json" \
     -d '{"orderId":"PX-1002","storeId":"0412","items":[{"sku":"10045","quantity":12}]}'
   ```

   The first command returns `Order API is running (orders go to Event Hubs)`. The second returns `{"orderId":"PX-1002","status":"Accepted"}`. This time the status is **Accepted**, not **Stored**, because the API hands the order off and doesn't process it. If you receive an error within a few minutes of the role assignments, wait and try again.

2. In the portal, open the `evh-orders-<unique>` namespace. On the **Overview** page, the **Messages** chart shows incoming and outgoing messages. Both rise after a short delay.
3. Open `func-orders-<unique>`, select `process_order`, and then select **Invocations**. A successful run appears after a short delay.
4. Show the processed order:

   ```bash
   az storage blob list --account-name $STORAGE --container-name processed-orders --auth-mode key --query "[].name" -o tsv
   az storage blob download --account-name $STORAGE --container-name processed-orders --name PX-1002.json --auth-mode key --file PX-1002.json -o none && cat PX-1002.json
   ```

   The file contains `"status": "Processed"`.

## Troubleshooting Part 2

| Symptom | Likely cause | Fix |
|---|---|---|
| Event Hubs shows incoming messages but no outgoing messages, and Application Insights shows "Failed to initialize scale monitoring" | The function app has no system-assigned identity, or the roles went to the `-uami` identity | Repeat Task 11.1 and its verification, and then assign the roles to the system-assigned identity. Restart the function app. |
| Same symptom, and the settings list from Task 12 shows `<unique>` | A placeholder wasn't replaced | Correct the settings in **Environment variables**, select **Apply**, and restart the function app. |
| "No job functions found" in the function logs, or `process_order` is missing | The code was deployed without `--build-remote true` | Run the deployment command in Task 13 again, and then restart. |
| `curl` still returns `Stored`, and no event reaches Event Hubs | The web app settings from Task 12.1 are missing | Add `EVENTHUB_FQDN` and `EVENTHUB_NAME`, and apply them. |
| `curl` returns 500 | The web app's Sender role (11.2) is missing, or `EVENTHUB_FQDN` is wrong | Check the role and the setting. Wait a few minutes after assigning the role. |
| The function runs but no blob appears in `processed-orders` | The function can't write to the storage account, or the container doesn't exist | Confirm the containers (Task 9) and Storage Blob Data Contributor for the system-assigned identity (11.4). If it still fails, assign **Storage Blob Data Owner** instead. |
| The order appears in `failed-orders` | The order failed validation | This is expected for an invalid order. Open the blob to read the reason. |

✅ **Checkpoint:** `PX-1002.json` exists in the `processed-orders` container.

## Part 2 knowledge check

1. Why does the API send each order to an event hub instead of processing it directly?
2. Which service hosts the API, which runs the order processor, and why does each fit its job?
3. What does `EventHubConnection__fullyQualifiedNamespace` contain, and why isn't it a secret?
4. Which identity has which role, at which scope? Why is each Event Hubs role scoped to the event hub?
5. An event hub has no dead-letter queue. What would you do with an order that fails validation? (Look at how the function in this lab handles it.)

---

# Cleanup

Don't delete anything yet. Lab 3 uses this environment and ends by deleting `rg-orders-lab-<unique>`. If you won't do Lab 3 today, delete the resource group now so that it stops incurring charges:

```bash
az group delete --name $RG --yes --no-wait
```

# Reference links

- [Azure Cloud Shell overview](https://learn.microsoft.com/en-us/azure/cloud-shell/overview)
- [Install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Quickstart: Deploy a Python web app to Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python)
- [Deploy files to App Service](https://learn.microsoft.com/en-us/azure/app-service/deploy-zip)
- [Use the Azure portal to create an event hub](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-create)
- [Azure Event Hubs trigger for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-event-hubs-trigger)
- [Azure Functions Flex Consumption plan hosting](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan)
- [Use identity-based connections with Azure Functions triggers and bindings](https://learn.microsoft.com/en-us/azure/azure-functions/functions-identity-based-connections-tutorial-2)
- [Package-based deployment for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/deployment-zip-push)
