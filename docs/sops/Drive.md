# SOP 03: Network Share and Common Drive Access

**Target Incidents:** Users requesting new access to shared drives, reporting mapped drives disappearing, or encountering "Access Denied" errors.
**Document Owner:** IT Operations / Identity & Access Management (IAM)
**Last Updated:** February 2026

---

## Chapter 1: Distributed File System (DFS) Basics

### 1.1 Overview of Enterprise Mapped Drives
In our enterprise environment, file shares are not mapped directly to a single physical server (e.g., `\\Server01\Finance`). Instead, we utilize Microsoft's Distributed File System (DFS) to create a logical namespace.



* **DFS Namespace:** Users connect to a unified, highly available namespace, typically structured as `\\corp.domain.com\Shares\`.
* **Folder Targets:** Behind the scenes, DFS routes the user's request to the closest physical file server based on their Active Directory site. If a server in New York goes down, DFS seamlessly redirects the user to a replicated server in Chicago.
* **Drive Mapping:** Group Policy Objects (GPOs) are used to automatically map these DFS namespaces to specific drive letters on the user's workstation during login (e.g., the `S:` drive for "Shared", the `H:` drive for "Home").

### 1.2 Understanding Active Directory Security Groups
Access to folders within the DFS namespace is governed by **Role-Based Access Control (RBAC)** using Active Directory (AD) Security Groups. We do not assign permissions directly to individual users.

* **AGDLP Principle:** We follow the Microsoft AGDLP best practice: **A**ccounts go into **G**lobal groups, which go into **D**omain **L**ocal groups, which are granted **P**ermissions.
* **Permission Types:** Every shared folder typically has two corresponding AD groups:
    * `SG_ShareName_RO` (Read-Only)
    * `SG_ShareName_RW` (Read/Write)
* **The "Access Denied" Rule:** If a user clicks a folder and receives "Access Denied", they are either missing from the required AD security group, or their local machine has not yet received an updated Kerberos authentication ticket reflecting their group membership.

---

## Chapter 2: Access Request Workflows

### 2.1 Verifying Manager / Data Owner Approvals
Because network shares often contain Personally Identifiable Information (PII) or sensitive financial data, IT cannot grant access based solely on a user's request. 

**Standard Approval Workflow:**
1. Review the ITSM ticket for documented approval.
2. If approval is missing, identify the **Data Owner** of the requested folder. (This is usually a Department Head or Director, tracked in the IT Knowledge Base or an IAM matrix).
3. If the Data Owner is unknown, the user's direct line manager must provide written approval in the ticket.
4. **Action:** If no approval is present, set the incident to "On Hold - Awaiting Caller" and reply: *"To comply with enterprise security policies, please attach written approval from your Manager or the Department Head authorizing your access to this folder."*

### 2.2 Adding Users to AD Security Groups
Once authorization is verified, L1/L2 engineers will provision the access via Active Directory.

**Execution Steps:**
1. Open **Active Directory Users and Computers (ADUC)** or the enterprise IAM web portal.
2. Search for the specific Security Group associated with the folder (e.g., `SG_Finance_Q3_RW`).
3. Double-click the group, navigate to the **Members** tab, and click **Add**.
4. Enter the user's AD username (SAMAccountName), click **Check Names**, and click **OK**.
5. Log this action in the ticket: *"User added to SG_Finance_Q3_RW per manager approval."*

### 2.3 Forcing AD Replication and Token Refreshes
A critical and often misunderstood concept: **Adding a user to an AD group does not instantly grant them access on their local PC.** Group memberships are embedded in the user's Kerberos Ticket Granting Ticket (TGT), which is generated at logon.

**Troubleshooting "I still can't access it":**
1. **Force AD Replication:** If your environment has multiple domain controllers, the change might not have synced. Run `repadmin /syncall` on the DC (if authorized) or wait 15 minutes.
2. **Purge Local Tickets:** Instruct the user to open Command Prompt and run the command `klist purge`. This clears old authentication tickets.
3. **The Gold Standard:** The most reliable way to force the PC to request a new Kerberos ticket with the updated group memberships is to instruct the user to **Log off and Log back into Windows**. (A simple restart also works, but a logoff is faster).

---

## Chapter 3: Troubleshooting Drive Mapping Failures

### 3.1 Manually Mapping Drives via Command Prompt (`net use`)
If Group Policy fails to map the drive automatically, you can manually map it to restore the user's productivity while investigating the root cause.

**Execution Steps:**
1. Open **Command Prompt** (does not need to be Administrator).
2. To see currently mapped drives, run: `net use`
3. To delete a stuck or corrupted drive mapping (e.g., the S: drive), run:
   `net use S: /delete /y`
4. To map the drive manually, run:
   `net use S: \\corp.domain.com\Shares\Finance /persistent:yes`
5. If the user is prompted for credentials, ensure they format their username as `DOMAIN\username`.

### 3.2 Troubleshooting Offline Files and Sync Center Conflicts
Windows "Offline Files" (Sync Center) allows users to access network files without an internet connection. However, its cache frequently corrupts, causing drives to appear with a "Grey X" or report as disconnected even when the network is healthy.

**Diagnostic & Remediation Steps:**
1. Navigate to **Control Panel > Sync Center > Manage offline files**.
2. If the user does not actually need offline access, click **Disable offline files** and restart the PC.
3. **Cache Corruption Fix:** If offline files are required but broken, you must format the database.
   * Open Registry Editor (`regedit`).
   * Navigate to: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\CSC\Parameters`
   * Create a new `DWORD (32-bit)` value named `FormatDatabase` and set its value to `1`.
   * Restart the computer. The registry key will delete itself and rebuild a fresh cache.

### 3.3 Resolving VPN/DNS Resolution Issues for File Servers
For remote users, drive mapping failures are almost always related to DNS resolution across the VPN tunnel.

**Diagnostic Steps:**
1. Verify the user is successfully connected to the VPN.
2. Attempt to ping the DFS namespace: `ping corp.domain.com`
   * If the ping resolves to an external IP instead of an internal Domain Controller IP, the VPN Split Tunnel DNS is failing.
3. Attempt to ping the specific file server directly. 
4. **Resolution:** * Flush the DNS cache (`ipconfig /flushdns`).
   * Verify that **NetBIOS over TCP/IP** is enabled on the VPN virtual network adapter (Network Connections > Properties > IPv4 > Advanced > WINS tab).

---

## Chapter 4: Previously Solved Incidents

### Incident: INC0000060
* **Symptom:** User stated: "Need access to the common drive for sharing files which can be accessed by all members. Please provide access."
* **Triage Performed:** The request was generic and lacked specific folder paths or approvals. Analyst checked the user's department (Marketing) and identified the standard Marketing Common Drive (`\\corp.domain.com\Shares\Marketing`).
* **Root Cause:** Standard onboarding request, but the automated provisioning script failed to place the user in the departmental security group during their first week.
* **Resolution:** Reached out to the Marketing Director for approval. Once obtained, added the user to `SG_Marketing_Share_RW` via ADUC. Instructed the user to log off and log back into Windows (SOP Step 2.3). User confirmed access was restored. 

### Incident: INC0000412
* **Symptom:** User working from home reported their `S:` drive had a red X on it. Clicking the drive resulted in "The network path was not found." Internet and email were working normally.
* **Triage Performed:** Confirmed the user was connected to the Cisco AnyConnect VPN. Had the user open Command Prompt and run `ping corp.domain.com`. The ping failed to resolve an IP address.
* **Root Cause:** The user's home router (IPv6 enabled) was prioritizing ISP DNS servers over the VPN's internal DNS servers, preventing the PC from finding the DFS namespace.
* **Resolution:** Executed `ipconfig /flushdns` (SOP Step 3.3) and disabled IPv6 on the physical Wi-Fi adapter. Mapped the drive manually using `net use S: \\corp.domain.com\Shares /persistent:yes` (SOP Step 3.1) to force the connection. Drive turned green and files were accessible.