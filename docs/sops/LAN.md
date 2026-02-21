# SOP 09: Local Area Network (LAN) & Wi-Fi Outages

**Target Incidents:** "Wireless access is down in my area", specific floor outages, intermittent Wi-Fi drops, and localized LAN disconnection alerts.
**Document Owner:** IT Operations / Network Engineering Team
**Last Updated:** February 2026

---

## Chapter 1: Defining the Blast Radius

### 1.1 Identifying the specific Access Point (AP) or Switch Stack
When a user submits a ticket stating "the Wi-Fi is down," L1 and L2 agents must immediately determine if this is a client-specific issue, a localized hardware failure (a single dead Access Point), or a broader infrastructural outage (an entire switch stack or floor).

**Diagnostic Steps for Triage:**
1. **Query the User's Exact Location:** Do not accept "I'm in the office." Ask for the specific Building, Floor, and nearest Pillar or Cubicle Number.
2. **Check the Ticket Volume:** Search the ITSM tool for other network-related incidents reported in the same location within the last 30 minutes.
   * *Single User:* Likely a client-side driver or configuration issue (Proceed to Chapter 3).
   * *Cluster of Users in One Zone:* Likely a single Access Point failure (Proceed to Chapter 2).
   * *Entire Floor:* Likely an Access Switch stack failure or upstream routing issue.
3. **Identify the Hardware via MAC Address:** If the user is partially connected but experiencing drops, ask them for their Wireless MAC Address (`ipconfig /all` -> Wireless LAN adapter -> Physical Address). Use this MAC address in the Wireless LAN Controller (WLC) to pinpoint exactly which AP they are currently roaming on.

### 1.2 Correlating User Location with Network Topologies
Once the physical location is established, engineers must correlate it with the logical network topology to understand upstream dependencies.



**Execution Steps:**
1. Open the Enterprise Network Management System (e.g., Cisco Prime, Meraki Dashboard, or Aruba AirWave).
2. Pull up the **Floor Plan / Heat Map** for the affected area.
3. Locate the nearest Access Point (e.g., `AP-NY-FL3-East`).
4. Cross-reference the AP's hostname in the CMDB to find its upstream connected switch (e.g., connected to `SW-NY-FL3-IDF-Stack1`, Port `Gi1/0/24`).
5. **Analysis:** If the AP is offline on the floor plan, check the adjacent APs. If all APs connected to `SW-NY-FL3-IDF-Stack1` are red/offline, the issue is not wireless; it is a catastrophic failure of the IDF (Intermediate Distribution Frame) switch stack. Escalate immediately to Network Engineering.

---

## Chapter 2: Access Point Troubleshooting

### 2.1 Checking Wireless Controller Dashboards (Cisco/Aruba)
Enterprise Wi-Fi is centrally managed by Wireless LAN Controllers (WLCs). The WLC dictates channel assignments, power levels, and client handoffs. 



**Execution Steps:**
1. Log into the WLC (or cloud dashboard like Meraki/Aruba Central) governing the affected site.
2. Search for the specific AP hostname identified in Chapter 1.
3. **Review AP Status:**
   * **Status: UP / Clients: 0:** The AP is broadcasting, but clients are failing to associate. This often points to a RADIUS/Authentication server timeout or DHCP failure.
   * **Status: DOWN:** The AP has lost communication with the controller. This indicates a physical cable fault, a PoE failure, or a dead AP.
   * **Channel Utilization:** Look at the 2.4GHz and 5GHz utilization metrics. If utilization is sustained above 80%, the AP is experiencing severe co-channel interference or is overloaded by too many clients. 
4. **Review Client Logs:** Search the WLC logs for the affected user's MAC address. Look for failure reason codes (e.g., `Reason Code 1: Unspecified`, or `Reason Code 15: 4-Way Handshake Timeout` indicating a bad password/certificate).

### 2.2 PoE (Power over Ethernet) Re-seating and Port Bouncing
Enterprise Access Points do not plug into wall outlets; they draw power directly from the network switch via Power over Ethernet (PoE). A common resolution for a frozen or unresponsive AP is to remotely cycle this power.

**Execution Steps (Remotely Bouncing an AP):**
1. Identify the upstream switch and port (from Step 1.2).
2. SSH into the switch using a terminal emulator (e.g., PuTTY or SecureCRT).
3. Enter privileged EXEC mode and configuration mode:
   ```text
   Switch> enable
   Switch# configure terminal