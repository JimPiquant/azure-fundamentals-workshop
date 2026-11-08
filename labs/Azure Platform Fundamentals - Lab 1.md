# Lab 1: Azure Platform Fundamentals

## Overview

In this lab, you will explore an Azure subscription, review resource providers and cost analysis, create a tagged resource group, deploy a storage account and a Linux virtual machine, inspect the virtual machine's network path, enable a system-assigned managed identity on the virtual machine, grant that identity data-plane access to Blob Storage, and then remove the complete lab environment.

**Estimated time:** 70–85 minutes (plus about 15 minutes for the optional challenge)  
**Level:** 100–200  
**Primary interface:** Azure portal

### How this lab maps to the module

| Decision | What you do | Tasks |
|---|---|---|
| Organize | Explore the subscription, resource providers, and Cost Analysis; create a tagged resource group | 1–2 |
| Place | Deploy a storage account and a small Linux virtual machine in Central US; record the redundancy and availability choices | 3–4 |
| Connect | Inspect the virtual machine's virtual network, subnet, network security group, effective security rules, and effective routes | 5 |
| Secure | Enable a managed identity and grant it a data role on the storage account | 6–7 |
| Clean up | Answer the knowledge check and delete the resource group | 8 |

## Learning objectives

After completing this lab, you should be able to:

- Identify important subscription properties and registered resource providers.
- Use Cost Analysis to review Azure consumption from different perspectives.
- Create a resource group and apply an organizational tag.
- Record the placement choices (region, redundancy, and availability) for the resources you deploy.
- Recognize the resources that support an Azure virtual machine.
- Inspect a virtual machine's network path: address space, subnet, network security group, effective security rules, and effective routes.
- Enable a system-assigned managed identity.
- Assign an Azure role to a managed identity at the correct scope.
- Delete a resource group to remove all resources it contains.

## Prerequisites

You need:

- Access to the [Azure portal](https://portal.azure.com/).
- An Azure subscription that you own, such as your MSDN subscription, with the **Active** state. As the subscription owner, you can create resources and role assignments.

> ❗ **IMPORTANT**
>
> Use the names, the **Central US** region, and the resource sizes in this lab. A virtual machine incurs charges while it exists. Complete the cleanup task even if you do not finish the optional challenge.

## Before you start: pre-flight check

Complete these checks before Task 1. They prevent the most common failures.

1. Sign in to the [Azure portal](https://portal.azure.com/) and confirm you can open **Subscriptions**.
2. Open your subscription and confirm that the subscription state is **Active**. A disabled subscription, for example one that has used its monthly credit, can't create resources.
3. Confirm that you can use a small virtual machine in Central US:
   1. In the portal search box, enter **Virtual machines**, and then select **Virtual machines**.
   2. Select **Create** > **Azure virtual machine**, and set **Region** to **(US) Central US**.
   3. Open the **Size** list, and confirm that `Standard_B1s` is available and not marked as restricted or lacking quota. If it isn't, note the smallest available size and use it in Task 4.
   4. Close the page without creating the virtual machine.
4. Check the resource providers listed in Task 1.2 now, and register any that are missing.

## Resource names

Azure resource names must often be unique. Replace `<unique>` with a short identifier that only you use, such as your initials plus three digits (for example, `jw482`). Use lowercase letters and numbers only, and use the same value in every lab.

| Resource | Suggested name |
|---|---|
| Resource group | `rg-platform-lab-<unique>` |
| Storage account | `stplatform<unique>` |
| Blob container | `labfiles` |
| Virtual machine | `vm-platform-<unique>` |
| Virtual network | Accept the portal-generated name or use `vnet-platform-<unique>` |

Storage-account names must be globally unique, 3–24 characters long, and contain only lowercase letters and numbers. We are adding the unique identifier to the other resources for consistency.

---

# Task 1: Explore the subscription (Organize)

## 1.1 Review subscription properties

1. Sign in to the [Azure portal](https://portal.azure.com/).
2. In the search box, enter **Subscriptions**, and then select **Subscriptions**.
3. Select your subscription.
4. On **Overview**, identify:
   - Subscription name
   - Subscription ID
   - Microsoft Entra tenant or directory
   - Subscription status
5. Do not copy the subscription ID into public notes, chat, or screenshots.

✅ **Checkpoint:** You can identify the subscription and directory in which the lab resources will be created.

## 1.2 Review resource providers

1. In the subscription menu, under **Settings**, select **Resource providers**.
2. Search (Filter by name...) for each of the following providers:
   - `Microsoft.Compute`
   - `Microsoft.Network`
   - `Microsoft.Storage`
3. Record whether each provider is **Registered**.
4. If a required provider is not registered, select it, and then select **Register**. Wait until the status changes to **Registered**.

💡 **Why this matters:** Azure Resource Manager routes management requests to resource providers. Virtual machines, networking resources, and storage accounts depend on the providers listed above.

## 1.3 Run Cost Analysis

1. Return to the subscription menu.
2. Under **Cost Management**, select **Cost analysis**.
3. If the portal offers multiple views, start with **Cost by resource** or the default accumulated-cost view.
4. Set an appropriate date range, such as **This month**.
5. Explore at least two groupings or views:
   - Resource group
   - Service name
   - Resource
   - Location
6. Apply a filter for a resource group or service if the subscription already contains data.
7. Observe whether the view shows actual cost, forecast cost, or no data.

> 📝 **NOTE**
>
> Newly created resources and charges might not appear immediately. Some training subscriptions also restrict Cost Management access. If cost data is unavailable, review the available controls and continue.

✅ **Checkpoint:** You can explain how tags, resource groups, services, and resources can support cost analysis.

---

# Task 2: Create and tag a resource group (Organize)

1. In the Azure portal search box, enter **Resource groups**, and then select **Resource groups**.
2. Select **+ Create**.
3. On the **Basics** tab:
   - Select your subscription.
   - Enter `rg-platform-lab-<unique>` as the resource-group name (see note above on resource names).
   - Select **(US) Central US** as the region (recommended, you can use others but resource allocations might fail).
4. Select **Next: Tags**.
5. Add this tag:

   | Name | Value |
   |---|---|
   | `Environment` | `development` |

6. Select **Review + create**, and then select **Create**.  This will submit a deployment job and return you to the list of resource groups.  In the toolbar in the top right a bell icon will indicate when it is complete or click the refresh button.
7. Open the new resource group and navigate to the Tags menu to verify that the tag is present.

✅ ✅ **Checkpoint:** The resource group exists and has the tag `Environment=development`.

**Discussion:** A resource group is a logical management container. It is not a network boundary, and resources in the group do not automatically share access permissions or network connectivity.

> 📝 **NOTE**
>
> Your own subscription has no Azure Policy assignments, so you don't expect policy errors in this lab. In a corporate tenant, a deployment can fail with **RequestDisallowedByPolicy**. The error names the policy that blocked it.

---

# Task 3: Deploy a storage account (Place)

## 3.1 Create the account

1. In the portal search box, enter **Storage accounts**, and then select **Storage accounts**.
2. Select **+ Create**.
3. On the **Basics** tab, configure:
   - **Subscription:** your subscription
   - **Resource group:** `rg-platform-lab-<unique>`
   - **Storage account name:** `stplatform<unique>`
   - **Region:** **(US) Central US**
   - **Primary Service** `Azure Blog Storage or Azure Data Lake Storage`
   - **Primary Workload** `General purpose`
   - **Performance:** Standard
   - **Redundancy:** Locally-redundant storage (LRS)
4. Keep the defaults on the remaining tabs.
5. Select **Review + create**, review the settings, and then select **Create**.
6. When deployment completes, select **Go to resource**.

## 3.2 Create a Blob container

1. In the storage-account menu, under **Data storage**, select **Containers**.
2. Select **+ Container**.
3. Enter `labfiles` as the name.
4. Leave **Anonymous access level** set to **Private (no anonymous access)**.
5. Select **Create**.

✅ ✅ **Checkpoint:** The storage account exists in the lab resource group.

**Place:** Record the region and the redundancy option you selected. Locally redundant storage (LRS) keeps three copies of the data within a single datacenter in the region; zone-redundant storage (ZRS) spreads copies across availability zones. Which failure can each option tolerate?

---

# Task 4: Deploy a small Linux virtual machine (Place)

1. In the portal search box, enter **Virtual machines**, and then select **Virtual machines**.
2. Select **Create** > **Virtual machine**.
3. On the **Basics** tab, configure:
   - **Subscription:** your subscription
   - **Resource group:** `rg-platform-lab-<unique>`
   - **Virtual machine name:** `vm-platform-<unique>`
   - **Region:** **(US) Central US**
   - **Availability options:** **No infrastructure redundancy required**. 
   - **Image:** **Ubuntu Server 24.04 LTS - x64 Gen2**
   - **Size:** `Standard_D2als_v7`, or the smallest size you identified in the pre-flight check (click on see all sizes to see all your options)
4. For the administrator account, set **Authentication type** to **SSH public key**, **Username** to `azureuser`, and **SSH public key source** to **Generate new key pair**. Select a key pair name, and download the private key when prompted. This lab never signs in to the virtual machine, so you can delete the key afterward.
5. Under **Inbound port rules**, set **Public inbound ports** to **None**. The lab does not need SSH access.
6. On the **Networking** tab, keep the default virtual network and subnet. Keep **Public IP** set to the new Standard public IP address that the portal proposes. The virtual machine has a public IP address; you use it in Task 5 and in the optional challenge.
7. On the **Disks**, **Management**, **Monitoring**, and **Advanced** tabs, keep the defaults.
8. On **Tags**, add:

   | Name | Value |
   |---|---|
   | `environment` | `development` |

9. Select **Review + create**, and then select **Create**.  Accept the private key download when prompted.
10. When deployment completes, select **Go to resource**.
11. Return to the resource group and review the resources created for the virtual machine. Depending on the selected configuration, these can include:
    - Network interface
    - Virtual network and subnet
    - Network security group
    - Operating-system disk
    - Public IP address, if one was requested

> 📝 **NOTE**
>
> Subnets in new virtual networks are private by default. A virtual machine in a private subnet has no outbound access to the internet or to public Azure endpoints unless it has an explicit outbound method, such as a public IP address associated with the virtual machine or a NAT gateway on the subnet.

✅ ✅ **Checkpoint:** The virtual machine is running, and you can identify the supporting resources in the resource group.

---

# Task 5: Inspect the network path (Connect)

Effective security rules and effective routes are available only while the virtual machine is running.

1. Open `vm-platform-<unique>`.
2. Expand **Networking**, and then select **Network settings**.
3. Identify and record:
   - The network interface name
   - The private IP address
   - The virtual network and subnet
   - The network security group
   - The public IP address, if any
4. Select the virtual network name. Record its address space. Under **Subnets**, record the address range of the subnet that contains the virtual machine.
5. Return to the virtual machine's **Network settings**, and select the network interface.
6. In the network interface menu, expand **Help**, and then select **Effective security rules**. Under `Click on a rule row to see the expanded list of prefixes.` click on the rule name to expand. Review the inbound and outbound rules. Identify the default rules `AllowVnetInBound`, `AllowAzureLoadBalancerInBound`, and `DenyAllInBound`.
7. Under **Help**, select **Effective routes**. Find the route for the virtual network's address space and the `0.0.0.0/0` route, and record each route's **Next hop type**.

✅ ✅ **Checkpoint:** You can state the virtual machine's private IP address and subnet, which inbound traffic its network security group allows, and where traffic to other destinations is routed.

**Discussion:** The resource group decided none of this. The virtual network, subnet, network security group, and routes control what can communicate. A route to the internet also doesn't guarantee outbound access by itself: in a private subnet, the virtual machine still needs an explicit outbound method.

---

# Task 6: Enable a system-assigned managed identity (Secure)

1. Open `vm-platform-<unique>`.
2. In the virtual-machine menu under **Security** select **Identity**.
3. On the **System assigned** tab, set **Status** to **On**.
4. Select **Save**, and then confirm the change.
5. After deployment completes, verify that the page shows an **Object (principal) ID**.

> 📝 **NOTE**
>
> The identity is created in Microsoft Entra ID and is tied to the lifecycle of this virtual machine. Azure removes the system-assigned identity when the virtual machine is deleted. If a user assigned managed identity was used it would have to be deleted manually or implicitly when the resource group is deleted.

✅ ✅ **Checkpoint:** The virtual machine has an enabled system-assigned managed identity.

---

# Task 7: Grant the virtual machine access to Blob Storage (Secure)

In this task, the storage account is the **scope**, `Storage Blob Data Contributor` is the **role**, and the virtual machine's system-assigned managed identity is the **security principal**.

1. Open the storage account `stplatform<unique>`.
2. Select **Access control (IAM)**.
3. Select **+ Add** > **Add role assignment**.
4. On the **Role** tab, search for and select **Storage Blob Data Contributor**.
5. Select **Next**.
6. On the **Members** tab:
   - For **Assign access to**, select **Managed identity**.
   - Select **+ Select members**.
   - Select your subscription.
   - For **Managed identity**, select **Virtual machine**.
   - Select `vm-platform-<unique>`.
   - Select **Select**.
7. Select **Review + assign**, review the assignment, and then select **Review + assign** again.
8. Return to **Access control (IAM)** > **Role assignments**.
9. Filter by **Storage Blob Data Contributor** or by the virtual-machine name and verify the assignment.

> ❗ **IMPORTANT**
>
> `Storage Blob Data Contributor` grants data-plane access to Blob Storage. It does not grant permission to manage the storage account itself. Role assignments can also require several minutes to propagate.

✅ ✅ **Checkpoint:** The virtual machine's managed identity has `Storage Blob Data Contributor` at the storage-account scope.

## Review the authorization model

Confirm that you can identify all four parts of the assignment:

| Element | Lab value |
|---|---|
| Security principal | System-assigned managed identity of `vm-platform-<unique>` |
| Role definition | `Storage Blob Data Contributor` |
| Scope | `stplatform<unique>` storage account |
| Effect | Read, write, and delete Blob data within that storage account |

---

# Optional challenge: Verify Blob access from the virtual machine

Complete this challenge only if sufficient time remains. You use **Run command**, which runs a script on the virtual machine through the Azure VM agent, so no SSH session or public inbound port is needed. Nothing needs to be installed on the virtual machine.

1. Open `vm-platform-<unique>`.
2. Under **Operations**, select **Run command**, and then select **RunShellScript**.
3. Paste the following script, replace `<unique>`, and select **Run**:

   ```bash
   # Ask the VM's local metadata endpoint for a token for Azure Storage.
   # No password, key, or connection string is involved.
   TOKEN=$(curl -s -H "Metadata: true" \
     "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://storage.azure.com/" \
     | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
   echo "Token received: ${#TOKEN} characters"

   # Upload a small blob by using the token. 201 means it worked.
   curl -s -o /dev/null -w "Upload result: %{http_code}\n" --max-time 20 -X PUT \
     -H "Authorization: Bearer $TOKEN" \
     -H "x-ms-version: 2021-08-06" \
     -H "x-ms-blob-type: BlockBlob" \
     --data "Managed identity access test" \
     "https://stplatform<unique>.blob.core.windows.net/labfiles/identity-test.txt"
   ```

4. Read the output:

   | Output | Meaning |
   |---|---|
   | `Upload result: 201` | Azure Storage accepted the managed identity's token and created the blob. |
   | `Upload result: 403` | The role assignment has not taken effect yet. Wait a few minutes and run the script again. |
   | `Upload result: 000` | The virtual machine could not reach the storage endpoint, usually because it is in a private subnet with no outbound method. The token request still worked, which proves the identity. Discuss with your instructor how a public IP address, a NAT gateway, or a private endpoint would provide the path. This lab's virtual machine has a public IP address, so you do not expect this result. |

5. If the upload succeeded, open the `labfiles` container in the portal and verify that `identity-test.txt` exists.

> 📝 **NOTE**
>
> If the Azure CLI is installed on the virtual machine, `az login --identity` followed by `az storage blob upload ... --auth-mode login` performs the same check.

---

# Task 8: Delete the resource group (Clean up)

Deleting the resource group removes the storage account, virtual machine, and all supporting resources contained in the group.

1. In the portal search box, enter **Resource groups**, and then select **Resource groups**.
2. Select `rg-platform-lab-<unique>`.
3. Review the resource list and confirm that it contains only your lab resources.
4. Select **Delete resource group**.
5. Enter the resource-group name when prompted.
6. Confirm the deletion.
7. Return to **Resource groups** and verify that the resource group is being deleted or no longer appears.

> ⚠️ **WARNING**
>
> Resource-group deletion is irreversible. Verify the resource-group name before confirming.

✅ ✅ **Final checkpoint:** The lab resource group and its resources have been deleted.

---

# Knowledge check

1. What is the difference between a subscription, a resource group, and an individual Azure resource?
2. Why might a resource provider need to be registered?
3. What information can Cost Analysis group or filter?
4. Does placing two resources in the same resource group automatically allow them to communicate?
5. Which default network security group rule blocks inbound traffic from the internet?
6. Why might a virtual machine with a route to the internet still be unable to reach a public endpoint?
7. What happens to a system-assigned managed identity when its Azure resource is deleted?
8. In the role assignment you created, what were the principal, role, and scope?
9. Why was a Blob data role used instead of a management-plane Contributor role?

# Reference links

- [Azure Resource Manager resource providers and types](https://learn.microsoft.com/azure/azure-resource-manager/management/resource-providers-and-types)
- [Analyze costs with Cost Analysis](https://learn.microsoft.com/azure/cost-management-billing/costs/quick-acm-cost-analysis)
- [Manage Azure resource groups by using the Azure portal](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)
- [Use tags to organize Azure resources and management hierarchy](https://learn.microsoft.com/azure/azure-resource-manager/management/tag-resources-portal)
- [Overview of Azure Policy](https://learn.microsoft.com/en-us/azure/governance/policy/overview)
- [Create an Azure storage account](https://learn.microsoft.com/azure/storage/common/storage-account-create)
- [Create a Linux virtual machine in the Azure portal](https://learn.microsoft.com/azure/virtual-machines/linux/quick-create-portal)
- [Diagnose a virtual machine network traffic filter problem](https://learn.microsoft.com/en-us/azure/virtual-network/diagnose-network-traffic-filter-problem)
- [Diagnose an Azure virtual machine routing problem](https://learn.microsoft.com/en-us/azure/virtual-network/diagnose-network-routing-problem)
- [Default outbound access in Azure](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access)
- [Configure managed identities on Azure virtual machines by using the Azure portal](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/qs-configure-portal-windows-vm)
- [Use Azure portal to grant a managed identity access to a resource](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/grant-managed-identity-resource-access-azure-portal)
- [Assign Azure roles by using the Azure portal](https://learn.microsoft.com/azure/role-based-access-control/role-assignments-portal)
- [Azure built-in roles for storage](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/storage)
- [Use managed identities on a virtual machine to acquire an access token](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token)
- [Run scripts in a Linux VM by using action Run Commands](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/run-command)
- [Put Blob (REST API)](https://learn.microsoft.com/en-us/rest/api/storageservices/put-blob)
- [Authorize access to Blob Storage with Azure CLI](https://learn.microsoft.com/azure/storage/blobs/authorize-data-operations-cli)
