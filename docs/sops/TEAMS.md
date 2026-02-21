# SOP 10: Collaboration Tools & Unified Communications

**Target Incidents:** General IT: Teams/Zoom audio failing, video freezing, meeting disconnects, and screen sharing failures.
**Document Owner:** IT Operations / Unified Communications (UC) Team
**Last Updated:** February 2026

---

## Chapter 1: Unified Communications Triage

### 1.1 Determining Global Cloud Outage vs. Local Application Failure
When a user reports that a collaboration tool (Microsoft Teams, Zoom, Webex) is failing, the very first step is to establish the scope of the failure. Collaboration tools are highly sensitive to both local resource exhaustion (CPU/RAM) and global cloud infrastructure health.

**Diagnostic Workflow:**
1. **Check Global Health Dashboards:**
   * **Microsoft Teams:** Navigate to the Microsoft 365 Admin Center -> Health -> Service health. Look for advisories specifically under "Microsoft Teams" (e.g., TMXXXXXX).
   * **Zoom:** Navigate to `status.zoom.us` to check for regional SIP/Telephony or Meeting Webhook degradation.
2. **Determine the Blast Radius:**
   * If the global dashboards are green, check the ITSM ticket queue. Are there 5+ tickets submitted in the last 15 minutes reporting dropped calls? If yes, this is likely an enterprise-wide network egress issue (Proceed to Chapter 3).
   * If it is a single user, or a handful of users working from home, the issue is highly localized to their endpoint or local ISP (Proceed to Chapter 2).
3. **Web Client Bypass Test:**
   * Instruct the user to close the desktop application and log into the web version of the tool (e.g., `teams.microsoft.com` or `zoom.us/join` via Edge or Chrome).
   * *Analysis:* If the web client works perfectly (audio and video are stable), the local desktop application is corrupted or experiencing cache issues. If the web client *also* fails, the issue is at the OS permission layer or local network layer.

---

## Chapter 2: Application-Level Fixes

### 2.1 Clearing Teams/Zoom Application Cache (`%appdata%`)
Desktop UC applications aggressively cache presence data, tenant configurations, and media device states. A corrupted cache is the number one cause of infinite loading loops, missing UI elements, and ghost hardware (e.g., the app sees a microphone that is no longer plugged in).

**Execution Steps for Microsoft Teams (Classic):**
1. Fully quit Teams. Right-click the Teams icon in the system tray (near the clock) and select **Quit**.
2. Press `Win + R` to open the Run dialog.
3. Type `%appdata%\Microsoft\Teams` and press Enter.
4. Delete all files and folders in this directory. (This will not delete user data or chat history, as that is stored in the cloud).
5. Restart Teams. It will prompt for a fresh login.

**Execution Steps for Microsoft Teams (New/V2):**
1. Fully quit Teams.
2. Press `Win + R`, type `cmd`, and press Enter.
3. Execute the following command to reset the UWP app package:
   `rmdir /q /s %localappdata%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache`
4. Restart Teams.

**Execution Steps for Zoom:**
1. Quit Zoom from the system tray.
2. Press `Win + R`, type `%appdata%\Zoom`, and press Enter.
3. Navigate into the `data` folder and clear the contents.
4. *Alternative GUI Method:* Open Zoom -> Settings (Gear Icon) -> Zoom Apps -> Clear, or use the "CleanZoom" executable provided by Zoom support for a deep scrub.

### 2.2 Verifying Application Permissions (Microphone/Camera Privacy Settings)
If the application launches successfully but the user cannot be heard or seen, and the hardware works in other apps, Windows Privacy settings are likely blocking the hardware stream.

**Execution Steps:**
1. **Microphone Privacy:**
   * Press `Win + I` to open Windows Settings.
   * Navigate to **Privacy & security** > **Microphone**.
   * Ensure **Microphone access** is toggled ON.
   * Ensure **Let apps access your microphone** is toggled ON.
   * Scroll down to the list of specific apps. Ensure Microsoft Teams / Zoom is toggled ON. (If using New Teams, check "Let desktop apps access your microphone" at the very bottom).
2. **Camera Privacy:**
   * Navigate to **Privacy & security** > **Camera**.
   * Verify the same three levels of access as the microphone.
3. **Exclusive Mode Conflict (Audio):**
   * Sometimes, another app (like Spotify or a softphone) takes exclusive control of the microphone.
   * Press `Win + R`, type `mmsys.cpl`, and press Enter.
   * Go to the **Recording** tab, right-click the headset -> **Properties** -> **Advanced**.
   * Uncheck "Allow applications to take exclusive control of this device".

---

## Chapter 3: Network & Bandwidth Diagnostics

### 3.1 Checking QoS (Quality of Service) policies on local routers
Voice over IP (VoIP) and Real-Time Video are highly sensitive to jitter, latency, and packet loss. Quality of Service (QoS) ensures that real-time collaboration traffic is prioritized over bulk data transfers (like someone downloading a large file).



**Diagnostic Steps (For Network/UC L2 Teams):**
1. **Verify DSCP Markings:** Collaboration apps tag their packets with specific Differentiated Services Code Point (DSCP) values. 
   * Audio is typically tagged as **EF (Expedited Forwarding) / DSCP 46**.
   * Video is typically tagged as **AF41 / DSCP 34**.
2. **Endpoint Validation:** Ensure Group Policy (GPO) is actually applying these tags at the Windows OS level.
   * Open `gpedit.msc` -> Computer Configuration -> Windows Settings -> Policy-based QoS. Verify policies exist for `Teams.exe` and `Zoom.exe`.
3. **Network Validation:** If users in a specific branch office experience robotic audio, log into the local branch router and check the QoS queue drops.
   * Command (Cisco): `show policy-map interface`
   * If packets are dropping in the Priority Queue, the branch's WAN link is severely congested, or the QoS policy is misconfigured.

### 3.2 Bypassing VPNs for Collaboration Traffic (Split Tunneling validation)
Routing real-time audio/video traffic through a corporate VPN concentrator introduces unnecessary hairpinning, latency, and packet fragmentation. Best practice dictates that UC traffic should bypass the VPN entirely (Split Tunneling) and go directly to the internet.



**Diagnostic Steps:**
1. **Verify VPN State:** Check if the user is connected to the Cisco AnyConnect or GlobalProtect VPN.
2. **Test Direct Egress:** We must confirm if Teams/Zoom is bypassing the tunnel.
   * Open Command Prompt and run a trace to the Teams transport relays: `tracert world.tr.teams.microsoft.com`
   * *Analysis:* If the first hop is the corporate VPN gateway (e.g., `10.50.1.1`), Split Tunneling is failing. The traffic is being hairpinned. If the first hop is the user's home ISP router (e.g., `192.168.1.1`), Split Tunneling is working.
3. **Check UDP Port Blockage:** UC apps strongly prefer UDP for media streams (Ports 3478-3481 for Teams). If a user's home router or the corporate firewall blocks outbound UDP, the app will fall back to TCP.
   * TCP fallback causes significant audio delay and video freezing.
   * *Resolution:* Instruct the user to reboot their home router. If on corporate Wi-Fi, verify with Network Security that outbound UDP 3478-3481 is permitted.

---

## Chapter 4: Previously Solved Incidents

### Incident: INC0000811
* **Symptom:** User stated, "My Teams is completely broken. It just shows a white screen and says 'Loading...' forever. I restarted my laptop twice."
* **Triage Performed:** Verified Microsoft 365 Health Dashboard; no global Teams outages. Instructed the user to log into the web version (`teams.microsoft.com`). The web version loaded perfectly and the user could join their meeting. This isolated the issue to the local desktop client.
* **Root Cause:** The local `%appdata%` cache for the Microsoft Teams desktop client was corrupted during a recent forced background update, causing an infinite UI rendering loop.
* **Resolution:** Walked the user through closing Teams via the system tray, opening the Run dialog, and deleting the contents of the `%appdata%\Microsoft\Teams` directory (SOP Step 2.1). Upon relaunching, Teams downloaded a fresh configuration from the cloud and loaded normally within 10 seconds.

### Incident: INC0000854
* **Symptom:** A remote user reported, "Every time I join a Zoom meeting while working from home, people say I sound like a robot and my video freezes. My internet speed test shows 500 Mbps."
* **Triage Performed:** Checked local PC resources (CPU/RAM) via Task Manager; all normal. Verified the user was connected to the corporate VPN. Instructed the user to disconnect from the VPN and rejoin the meeting. The audio and video quality immediately became crystal clear.
* **Root Cause:** The corporate VPN client (Cisco AnyConnect) had a corrupted XML profile that failed to apply the Split Tunneling rules (SOP Step 3.2). All of the user's high-bandwidth Zoom UDP traffic was being forced through the corporate datacenter firewall, which was throttling the connection.
* **Resolution:** Reinstalled the VPN client via the Software Center to pull down the correct, updated Split Tunnel routing table. After reconnecting to the VPN, Zoom traffic successfully bypassed the corporate tunnel, and meeting quality remained stable.