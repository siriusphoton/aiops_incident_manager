# SOP 01: SAP Enterprise Application Suite Troubleshooting

**Target Incidents:** SAP HR, Finance, Controlling, Sales, and Materials modules hanging, timing out, or entirely inaccessible.
**Document Owner:** IT Operations / Major Incident Management
**Last Updated:** February 2026

---

## Chapter 1: Overview of SAP Modules & Architecture

### 1.1 Differentiating Module Errors vs. Core Outages
When troubleshooting SAP, Level 1 and Level 2 engineers must immediately determine if the reported issue is isolated to a specific module (e.g., SAP HR or SAP Finance) or if it represents a systemic failure of the core SAP ERP environment (ECC or S/4HANA). 

* **Module-Specific Errors:** These usually manifest as specific ABAP short dumps, authorization errors (e.g., `SU53` authorization failures), or missing data in specific transaction codes (T-Codes). If users in SAP Finance can work perfectly while SAP HR users experience timeouts, the issue is typically at the application configuration or specific application server level.
* **Core Outages:** If users across multiple modules (HR, Finance, Sales) report identical symptoms simultaneously, the issue is a Core Outage. Symptoms include the SAP Logon Pad failing to connect (Error: `WSAEWOULDBLOCK` or `10054`), HTTP 503 Service Unavailable errors on the SAP Fiori Launchpad, or universal freezing when trying to save any transaction. Core outages point to the database, the core network, or the central load balancer.

### 1.2 Understanding the SAP HANA Database Backbone
Modern SAP environments operate on a 3-tier architecture: Presentation (SAP GUI / Fiori Browser), Application (SAP NetWeaver / ABAP servers), and Database (SAP HANA). 



SAP HANA is an in-memory database. Because it processes data in RAM rather than on physical disks, it is incredibly fast but highly sensitive to memory saturation and CPU spikes. 
* **The "Hanging" Domino Effect:** If a poorly written financial query locks a table in the SAP HANA database, the Application layer will continue to accept user requests but will be unable to commit them. The Application layer's work processes (dialog processes) will queue up and eventually exhaust all available connections. To the end-user, the application appears to "hang" indefinitely with a spinning hourglass. 
* **Diagnostic Rule:** A hanging application is almost always a Database lock or an Application process queue exhaustion, not a client-side PC issue.

---

## Chapter 2: Initial Triage & Impact Assessment

### 2.1 Single-User vs. Multi-User Triage (Blast Radius)
Before initiating any complex technical diagnostics, you must define the blast radius of the incident.

1. **Check the Incident Queue:** Filter the IT Service Management (ITSM) dashboard for incidents created in the last 30 minutes containing keywords: "SAP", "HANA", "Fiori", "HR", "Finance", "hanging", "spinning".
2. **Single-User Protocol:** If only one user is affected, do not escalate to the Basis or DBA teams. 
    * Verify their network connection.
    * Check their specific SAP GUI patch level.
    * Instruct the user to clear their SAP GUI cache or browser cache (for Fiori).
3. **Multi-User Protocol (The Threshold):** If 3 or more users from different locations or departments report the same SAP connectivity or hanging issue within a 15-minute window, declare a **Multi-User Outage**. Immediately upgrade the incident Impact to "1" (Enterprise) and proceed to Network/Database triage.

### 2.2 Authentication (SSO) vs. Application Loading Failures
It is critical to distinguish between a user who cannot *authenticate* and a user who cannot *load* the application data.

* **Single Sign-On (SSO) Failures:** If the enterprise uses SAML 2.0 via Microsoft Entra ID or Okta, an expired certificate or identity provider outage will block SAP access. 
    * **Symptoms:** User sees a Microsoft/Okta error page, a "SAML2.0 authentication failed" message, or an endless redirect loop at the login screen.
    * **Action:** Do not troubleshoot SAP. Route the ticket to the Identity and Access Management (IAM) team.
* **Application Loading Failures:** If the user successfully authenticates (they see their username in the top right corner) but the SAP Fiori tiles do not load, or clicking a tile results in a blank screen or timeout, the SSO layer is healthy. The issue resides in the SAP Application or Database tier.

---

## Chapter 3: Network & Load Balancer Diagnostics

### 3.1 Verifying F5 Load Balancer Health
Enterprise SAP environments use hardware load balancers (like F5 BIG-IP Local Traffic Manager) to distribute traffic across multiple SAP Application servers. If the F5 marks these servers as "offline" or if the F5 itself is dropping packets, SAP will appear completely down.

**Diagnostic Steps for L1/L2:**
1. Log into the F5 BIG-IP Management Console or check the Network Operations Center (NOC) monitoring dashboard (e.g., SolarWinds, Datadog).
2. Navigate to **Local Traffic** > **Pools** > **Pool List**.
3. Locate the pool designated for SAP (e.g., `POOL_SAP_PRD_443` or `POOL_SAP_PRD_3200`).
4. Check the Pool Status:
    * **Green (Available):** All nodes are healthy. The F5 is routing traffic properly.
    * **Yellow/Red (Offline/Warning):** One or more SAP application nodes have failed their health monitors. 
5. **Action:** If all pool members are red, the F5 is blocking all traffic because it believes SAP is down. Take a screenshot of the F5 pool status to include in your escalation notes.

### 3.2 Checking Network Latency to SAP Clusters
If the F5 is healthy, rule out basic network routing issues between the user subnets and the datacenter hosting SAP.

**Diagnostic Steps:**
1. Open a Command Prompt or PowerShell window from a machine experiencing the issue (or a jump host in the same subnet).
2. Run `ping [SAP_Virtual_IP]` to check for packet loss.
3. Run a `tracert [SAP_Virtual_IP]` to identify where traffic is halting. 
4. **Port Validation:** SAP GUI relies on port 3200 (or 32XX depending on the instance number), and SAP Fiori relies on 443 (HTTPS). Use PowerShell to test the port connection:
   `Test-NetConnection -ComputerName [SAP_Virtual_IP] -Port 443`
5. **Action:** If the `TcpTestSucceeded` returns `False`, there is a network firewall or routing issue. Route to the Network Security team.

---

## Chapter 4: Escalation & Failover Protocols

### 4.1 Routing to SAP Basis Team
The SAP Basis team is responsible for the health of the SAP NetWeaver Application layer. 

**When to Escalate to Basis:**
* Users are receiving explicit ABAP runtime errors (e.g., `SYSTEM_CORE_DUMPED`, `TSV_TNEW_PAGE_ALLOC_FAILED`).
* The F5 Load Balancer shows the application nodes are active, but users are experiencing infinite hanging (indicating exhausted dialog work processes in transaction `SM50`).
* Specific background jobs are failing system-wide.

**Required Escalation Payload:**
When updating the ticket for the Basis team, include:
* Exact error message or screenshot.
* Time of occurrence.
* Blast radius (number of users/locations affected).
* Confirmation that network and SSO have been validated.

### 4.2 Routing to Database Administration (DBA)
The DBA team is responsible for the SAP HANA database layer. Escalate to DBAs when the issue is fundamentally related to data retrieval or database health.

**When to Escalate to DBA:**
* Monitoring tools (Dynatrace/AppDynamics) trigger alerts for "HANA High Memory Utilization" or "HANA CPU Spikes".
* Basis teams report that application servers are healthy but are waiting on database locks.
* SAP HANA failover alerts have been triggered in the NOC.

**Required Escalation Payload:**
When routing to DBA, explicitly state: *"Automated triage indicates healthy Network/SSO/Application layers. Suspected HANA Database lock or resource exhaustion. Requesting immediate HANA health check."*

---

## Chapter 5: Previously Solved Incidents

This section documents historical incidents to aid the AI and human agents in recognizing patterns and expediting resolutions.

### Incident: INC0000051, INC0000052, INC0000053 (Grouped Outage)
* **Symptom:** Users across HR, Finance, and Sales reported that their SAP Fiori tiles were clicking but endlessly spinning. No error messages were displayed, just a hanging interface.
* **Triage Performed:** Network pings to the F5 load balancer were successful (`Test-NetConnection` on port 443 succeeded). SSO login via Microsoft Entra was successful. 
* **Root Cause:** A poorly optimized custom ABAP report was executed by the Finance team, which requested millions of rows without a limiting parameter. This caused a massive table lock in the SAP HANA database. As other modules (HR, Sales) attempted to read from shared tables, their requests queued up, eventually exhausting all available SAP Dialog processes.
* **Resolution:** Escalated to the SAP DBA team. The DBAs identified the locking thread via HANA Studio, terminated the rogue query, and flushed the application queues. Service was restored. 
* **Prevention:** Basis team implemented stricter timeout parameters for background reports.

### Incident: INC0000889
* **Symptom:** All remote VPN users reported that SAP GUI was instantly terminating with error `WSAECONNREFUSED: Connection refused`. Office-based users were working without issue.
* **Triage Performed:** Validated that the issue was multi-user but restricted strictly to the VPN IP subnet. 
* **Root Cause:** A scheduled firewall policy update on the core Palo Alto network firewall accidentally dropped the rule allowing traffic from the VPN subnet (`10.50.x.x`) to the SAP Datacenter VLAN on TCP Port 3200.
* **Resolution:** Escalated to Network Security team. The firewall rule was reverted to its previous state. Connectivity was restored immediately without requiring any SAP Basis intervention.