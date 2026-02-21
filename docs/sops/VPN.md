# SOP 02: VPN and Remote Access Connectivity

**Target Incidents:** Users unable to launch VPN clients post-update, connection drops, authentication timeouts, and virtual adapter failures.
**Document Owner:** IT Operations / Network Security Team
**Last Updated:** February 2026

---

## Chapter 1: VPN Infrastructure Overview

### 1.1 Supported Clients (Cisco AnyConnect, GlobalProtect, etc.)
Our enterprise environment currently supports two primary Virtual Private Network (VPN) clients, deployed based on user role and regional gateway proximity:
* **Cisco AnyConnect Secure Mobility Client:** The primary VPN client for 80% of the workforce. Utilizes SSL/TLS for secure tunneling to the core datacenter ASAv firewalls.
* **Palo Alto GlobalProtect:** Utilized primarily by high-security engineering teams and external contractors connecting to isolated DMZ environments. 

Service Desk analysts must first determine which client the user is attempting to launch, as the backend infrastructure, gateways, and client-side virtual adapters differ significantly.

### 1.2 Full Tunnel vs. Split Tunnel Configurations
It is critical to understand how user traffic is routed when connected, as this affects how you troubleshoot internet vs. internal connectivity issues.



* **Full Tunnel:** All network traffic from the user's machine (both internal corporate requests and general internet browsing) is forced through the VPN tunnel. 
    * *Symptom:* If the VPN is slow, the user's entire internet experience will be slow.
* **Split Tunnel:** Only traffic destined for corporate IP subnets (e.g., `10.x.x.x`) is routed through the VPN. General internet traffic (like YouTube or Zoom) goes directly out of the user's local ISP connection.
    * *Symptom:* The user can browse the internet perfectly fine, but cannot ping internal servers or access internal mapped drives.

---

## Chapter 2: Client-Side Diagnostics

### 2.1 Verifying Windows Software Update Conflicts
A common cause of VPN failure (specifically the VPN client failing to launch or crashing immediately) is a conflict introduced by a recent Windows OS update or cumulative patch.

**Diagnostic Steps:**
1. Open the **Run** dialog (`Win + R`) and type `appwiz.cpl` to open Programs and Features.
2. Click **View installed updates** on the left pane.
3. Check the "Installed On" date for the most recent Windows Cumulative Updates.
4. If an update was installed within the last 24-48 hours that aligns with the user's reported breakage, check the enterprise Known Errors database. 
5. *Temporary Fix:* If approved by Network Security, you can uninstall the conflicting patch using the command line: `wusa /uninstall /kb:XXXXXXX /quiet /norestart`. 

### 2.2 Virtual Network Adapter Driver Checks
VPN clients rely on a virtual network interface card (NIC) to route traffic. If this driver is corrupted, the client will fail to establish a connection.

**Diagnostic Steps:**
1. Open **Device Manager** (`devmgmt.msc`).
2. Expand the **Network adapters** section.
3. Look for the virtual adapter (e.g., "Cisco AnyConnect Secure Mobility Client Virtual Miniport Adapter for Windows" or "Palo Alto Networks Virtual Adapter").
4. **Identify Issues:**
    * If there is a **Yellow Warning Triangle**, the driver has crashed.
    * If the adapter is **missing**, the installation is corrupted.
5. **Resolution:** Right-click the virtual adapter and select **Disable device**. Wait 10 seconds, right-click again, and select **Enable device**. If the yellow triangle persists, proceed to Chapter 4 (Reinstallation).

### 2.3 Flushing DNS and Resetting TCP/IP Stacks
If the VPN connects successfully but the user cannot access internal resources by their hostname (e.g., `http://intranet`), the issue is likely a localized DNS cache corruption or a tangled TCP/IP stack.

**Diagnostic Steps:**
1. Open **Command Prompt** as Administrator.
2. Execute the following commands in sequence to flush stale routing and DNS data:
    * `ipconfig /release`
    * `ipconfig /flushdns`
    * `ipconfig /renew`
3. Execute the TCP/IP and Winsock reset commands to rebuild the network stack:
    * `netsh int ip reset`
    * `netsh winsock reset`
4. **Action:** Instruct the user to restart their computer. This is mandatory for the Winsock reset to take effect.

---

## Chapter 3: Authentication & Security Checks

### 3.1 MFA/RADIUS Server Timeouts
Users authenticating to the VPN must pass both Active Directory credentials and Multi-Factor Authentication (MFA). If the RADIUS server bridging the VPN gateway and the MFA provider experiences latency, the client will time out.

**Symptoms:**
* The user enters their username and password, hits "Connect", but never receives the push notification on their phone. The client spins for 30-60 seconds and returns a "Connection Attempt Failed" error.

**Diagnostic Steps:**
1. Verify the user's mobile device has cellular or Wi-Fi connectivity to receive the push notification.
2. Log into the MFA Administration Console (e.g., Duo Admin Panel or Okta Dashboard).
3. Search for the user's recent authentication logs.
4. **Action:** If the logs show "Authentication timed out" or "User ignored push", instruct the user to open the MFA app manually and ensure it is refreshing. If the logs show *no* recent attempts, escalate to the Network team to check the RADIUS server bridging.

### 3.2 Certificate Expiration Checks
Many corporate environments use machine-level or user-level certificates for VPN authentication instead of (or in addition to) passwords.

**Diagnostic Steps:**
1. Press `Win + R`, type `certmgr.msc` for User Certificates, or `certlm.msc` for Local Machine Certificates, and press Enter.
2. Navigate to **Personal** > **Certificates**.
3. Look for the certificate issued by the corporate internal Certificate Authority (CA).
4. Check the **Expiration Date** column.
5. **Action:** If the certificate is expired or missing, the user must connect their machine to the corporate network physically (via LAN cable in an office) to automatically pull a new certificate via Group Policy, or L1 must manually push a new certificate via the MDM portal.

---

## Chapter 4: Client Reinstallation Workflows

### 4.1 Clean Uninstallation using Scripted Tools
If the virtual adapter is corrupted or the application files are damaged, a standard uninstallation often leaves behind broken registry keys. A clean, scripted uninstall is required.

**Execution Steps:**
1. Open **PowerShell** as Administrator.
2. Stop the running VPN services:
    ```powershell
    Stop-Service -Name "vpnagent" -Force
    ```
3. Execute the WMIC uninstall command:
    ```powershell
    wmic product where "name like '%%Cisco AnyConnect%%'" call uninstall /nointeractive
    ```
4. Manually delete residual folders:
    * `C:\ProgramData\Cisco\Cisco AnyConnect Secure Mobility Client`
    * `C:\Users\%username%\AppData\Local\Cisco`
5. Restart the computer.

### 4.2 Pushing New Client Packages via SCCM/Intune
Once the corrupted client is completely removed, do not use manual executable files to reinstall, as they may lack the proper enterprise XML configuration profiles.

**Execution Steps:**
1. Instruct the user to open the **Software Center** (SCCM) or **Company Portal** (Intune) application on their desktop.
2. Search for "VPN Client" or "Cisco AnyConnect".
3. Click **Install**. 
4. This deployment method ensures that the corporate XML profile (which contains the gateway addresses and security settings) is correctly injected into the `ProgramData` directory during installation.
5. Once installed, ask the user to launch the client. The gateway drop-down should automatically be populated.

---

## Chapter 5: Previously Solved Incidents

### Incident: INC0000015
* **Symptom:** User reported: "I can't launch my VPN client since the last software update." The Cisco AnyConnect application would open for 2 seconds and instantly crash to desktop.
* **Triage Performed:** Reviewed Windows Event Viewer (Application logs). Found Event ID 1000 pointing to a faulting module `vpnagent.exe`. Checked Device Manager and found the Cisco Virtual Adapter was missing entirely.
* **Root Cause:** A Windows 11 Cumulative Update altered the driver signature enforcement registry keys, causing the OS to quarantine the VPN's virtual network adapter. 
* **Resolution:** Performed a Clean Uninstallation (SOP Step 4.1) to remove the corrupted remnants. Directed the user to Software Center to reinstall the client (SOP Step 4.2). The new installation correctly registered the virtual adapter under the new OS patch level. VPN connectivity was successfully restored.

### Incident: INC0000304
* **Symptom:** User stated they were "connected to the VPN" but could not open the corporate intranet or access any shared drives. Internet browsing (Google, news sites) was working perfectly.
* **Triage Performed:** Analyst confirmed via screen share that the VPN status was "Connected". Ran `ipconfig /all` and noted the user had successfully received a `10.50.x.x` IP address from the VPN pool. Pinging the intranet server by hostname (`ping intranet.corp.local`) resulted in "Ping request could not find host."
* **Root Cause:** The user's home ISP router was handing out IPv6 DNS addresses that were taking priority over the IPv4 DNS servers injected by the VPN's Split Tunnel configuration. 
* **Resolution:** Analyst executed the command `ipconfig /flushdns` followed by `netsh int ip reset` (SOP Step 2.3). Analyst also disabled IPv6 on the user's physical Wi-Fi adapter to force IPv4 routing. User restarted the PC, reconnected to the VPN, and internal DNS resolution was restored.