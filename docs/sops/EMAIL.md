# SOP 04: Email Server & Client Connectivity

**Target Incidents:** Email server down, Outlook disconnected, inability to send/receive, stuck outboxes, and bounce-backs.
**Document Owner:** IT Operations / Enterprise Messaging Team
**Last Updated:** February 2026

---

## Chapter 1: Enterprise Messaging Architecture

### 1.1 Cloud (M365) vs. On-Premise Exchange Routing
To troubleshoot email effectively, support engineers must understand the underlying messaging architecture. Our environment operates in a **Hybrid Exchange Model**:
* **Microsoft 365 (Exchange Online):** The majority of user mailboxes are hosted in the cloud. Mail routing for these users goes directly from the local Outlook client to Microsoft's datacenters via secure HTTPS connections.
* **On-Premise Exchange:** Certain service accounts, legacy applications, and highly regulated user mailboxes remain on-premise. Mail flow for these accounts relies on local Exchange servers and internal routing protocols.
* **The Hybrid Flow:** Emails sent between cloud mailboxes and on-premise mailboxes pass through secure hybrid connectors. If a user states "I can email external clients but not my internal colleagues," this hybrid connector is often the point of failure.

### 1.2 Essential Mail Ports (25, 443, 587)
Network firewalls or local PC security software can block essential ports, causing immediate client disconnection or send/receive failures.
* **Port 443 (HTTPS):** The modern backbone of Outlook and Exchange Web Services (EWS) / MAPI over HTTP. If Port 443 is blocked, Outlook will display "Disconnected" in the bottom right corner, and Outlook on the Web (OWA) will fail to load.
* **Port 25 (SMTP):** Used for server-to-server mail relay. Legacy applications (printers, scanners, old web apps) use this port to send internal mail. It should generally be blocked for end-user client submission.
* **Port 587 (SMTP Submission):** Used by clients (like mobile devices or third-party IMAP/SMTP apps) to submit secure, authenticated outgoing mail to the Exchange server.

---

## Chapter 2: Client-Level (Outlook) Troubleshooting

### 2.1 Launching in Safe Mode and Disabling Add-ins
If Outlook is crashing, hanging on the "Loading Profile" splash screen, or running extremely slowly, a third-party COM Add-in (e.g., WebEx, Zoom, Salesforce, or PDF readers) is usually the culprit.

**Diagnostic Steps:**
1. Close Outlook completely (verify `OUTLOOK.EXE` is not running in Task Manager).
2. Press `Win + R` to open the Run dialog.
3. Type `outlook.exe /safe` and press Enter.
4. **Analysis:** If Outlook launches perfectly in Safe Mode, an Add-in is causing the issue.
5. **Resolution (Disabling Add-ins):**
    * While in Safe Mode, go to **File** > **Options** > **Add-ins**.
    * At the bottom, next to "Manage: COM Add-ins", click **Go...**
    * Uncheck all non-essential add-ins, click **OK**, and restart Outlook normally. Re-enable them one by one to isolate the bad plugin.

### 2.2 Rebuilding the OST / Local Mail Profile
If Outlook states "Disconnected", folders are not syncing, or the user is getting generic send/receive errors (e.g., `0x8004010F`), the local cached data file (`.ost`) or the Mail Profile is corrupted.

**Option A: Rebuilding the OST File (Non-Destructive)**
1. Close Outlook.
2. Navigate to `C:\Users\%username%\AppData\Local\Microsoft\Outlook`.
3. Locate the user's email file (e.g., `john.doe@domain.com.ost`).
4. Rename it to `john.doe@domain.com.ost.OLD`.
5. Restart Outlook. It will automatically create a new `.ost` file and begin downloading mail from the server. (Note: This may take a while depending on mailbox size).

**Option B: Creating a New Mail Profile (If OST rebuild fails)**
1. Close Outlook.
2. Open **Control Panel** and search for **Mail (Microsoft Outlook)**.
3. Click **Show Profiles...**
4. Click **Add...**, name the new profile "Profile2", and walk through the Auto Setup wizard.
5. In the Mail window, select "Always use this profile" and choose "Profile2" from the dropdown. 
6. Launch Outlook.

### 2.3 Checking AutoDiscover DNS Records
If a user is trying to set up Outlook on a new machine and it repeatedly fails to find the server settings, the AutoDiscover process is failing.

**Diagnostic Steps:**
1. Hold the `CTRL` key and right-click the Outlook icon in the Windows System Tray (near the clock).
2. Select **Test E-mail AutoConfiguration**.
3. Enter the user's email address and password. Uncheck "Use Guessmart" but leave "Use AutoDiscover" checked.
4. Click **Test**.
5. **Analysis:** Review the Log tab. If it fails to locate `https://autodiscover.domain.com/autodiscover/autodiscover.xml`, there is an internal DNS issue or the user's machine cannot reach the domain controllers.

---

## Chapter 3: Server-Level & Network Diagnostics

### 3.1 Checking Mail Flow and Stuck Queues
If an entire department reports that emails are stuck in their Outbox, or external emails are severely delayed, the issue is at the server routing level.

**Diagnostic Steps for L2/Messaging Team:**
1. **For M365 (Cloud):**
    * Log into the Exchange Admin Center (EAC).
    * Navigate to **Mail flow** > **Message trace**.
    * Run a trace for the affected sender. If the trace shows "Pending" or "Failed", check the M365 Service Health Dashboard for active Exchange Online advisories.
2. **For On-Premise Exchange:**
    * Open the Exchange Management Shell (EMS).
    * Run the command: `Get-Queue`
    * **Analysis:** Normal queues should be close to `0`. If the `MessageCount` on the Hub Transport or Edge Transport servers is in the hundreds or thousands, the queue is stuck. Restarting the `MSExchangeTransport` service may be required.

### 3.2 Verifying External Gateway / Spam Filter Outages
Enterprise environments use external Secure Email Gateways (SEGs) like Proofpoint, Mimecast, or Barracuda to filter spam and malware before it reaches Exchange.

* **Symptom:** Internal emails work perfectly, but NO external emails are coming in or going out.
* **Diagnostic Steps:**
    1. Log into the Gateway Administration Console (e.g., Mimecast Admin Portal).
    2. Check the **Delivery Queues** or **Deferred Messages**.
    3. Verify the connection status between the Gateway and Microsoft 365 / On-Premise Exchange.
    4. Use a public tool like `mxtoolbox.com` to verify that the enterprise MX records are still correctly pointing to the Gateway.

---

## Chapter 4: Escalation Procedures

### 4.1 Invoking Major Incident for Enterprise-wide Outages
Email is a Tier-0 critical business service. 

**Thresholds for Major Incident Declaration:**
* **Volume:** 5 or more incidents logged within 15 minutes reporting complete email failure from different users.
* **Scope:** Both external incoming and outgoing mail are completely halted.
* **M365 Outage:** The Microsoft 365 Admin Portal shows a red "Service degradation" alert for Exchange Online.

**Escalation Workflow:**
1. If the threshold is met, L1 must immediately escalate the incident Impact to "1" (High) and Urgency to "1" (High).
2. Trigger the "Major Incident" workflow in ServiceNow to notify the Duty Manager.
3. Route the ticket directly to the **Unified Communications / Messaging Team**. 
4. Include the following details in the Work Notes:
   * "Automated Impact Assessment: Enterprise-wide Mail flow halted."
   * State whether internal mail is affected, external mail, or both.
   * State whether the M365 dashboard shows any active advisories.

---

## Chapter 5: Previously Solved Incidents

### Incident: INC0000032
* **Symptom:** User stated "EMAIL Server Down Again" and was extremely frustrated. They reported that Outlook constantly prompted for a password but would not accept their credentials.
* **Triage Performed:** Checked M365 Service Health - all green. Had the user launch Outlook in Safe Mode; issue persisted. Noticed the user recently changed their Active Directory password.
* **Root Cause:** The Windows Credential Manager had cached an expired/corrupted authentication token, preventing Outlook from fetching a modern OAuth token from Microsoft Entra ID.
* **Resolution:** Closed Outlook. Opened Windows Credential Manager and deleted all entries starting with `MicrosoftOffice16_Data`. Instructed the user to reopen Outlook. They were prompted for Modern Authentication (MFA), entered their new password, and connection was instantly restored.

### Incident: INC0000047, INC0000060 (Correlated Outage)
* **Symptom:** Multiple users from the Sales and Marketing departments submitted tickets stating "Issue with email" and "Cannot connect to email server." All users were receiving a "Disconnected" status in the Outlook desktop app.
* **Triage Performed:** Verified this was a multi-user issue affecting multiple floors. Checked OWA (Outlook on the Web) - users could access their mail via the web browser perfectly fine, isolating the issue to the Desktop Client network path. 
* **Root Cause:** A recent network firewall change accidentally blocked outbound TCP port 443 traffic for a specific employee VLAN, preventing the Outlook desktop client from reaching Microsoft's Exchange Online endpoints.
* **Resolution:** Escalated to Network Security. The firewall rule was immediately rolled back, restoring Port 443 access. Users restarted Outlook and reconnected successfully.