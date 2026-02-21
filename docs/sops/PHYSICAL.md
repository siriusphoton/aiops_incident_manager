# SOP 07: Datacenter Environmental Hazards & Physical Failures

**Target Incidents:** Rain/water leaking on server racks, HVAC/CRAC unit failures causing thermal runaway, physical infrastructure damage, and fire suppression deployments.
**Document Owner:** Datacenter Operations / Major Incident Management
**Last Updated:** February 2026

---

## Chapter 1: Emergency Physical Response Protocols

### 1.1 Life Safety and Electrical Hazard Assessment
In any datacenter environmental hazard scenario (water ingress, smoke, fire, or structural collapse), the preservation of human life supersedes all data and hardware availability concerns. IT equipment can be replaced; human lives cannot.

**Immediate Action Plan for On-Site Personnel:**
1. **Halt and Assess:** Do not rush into the affected aisle. Stop at a safe distance and perform a visual assessment.
2. **Identify the Hazard:**
   * **Water/Leaks:** If water is actively falling on powered server racks (e.g., from a roof leak or burst pipe), **DO NOT TOUCH** the racks, cables, or the standing water. The risk of lethal electrocution is extreme.
   * **Thermal/Smoke:** If smoke or the smell of burning electronics is present, evacuate the immediate aisle. Ensure you are not in the discharge zone of the FM-200 or Inergen fire suppression systems.
3. **Notify Security and NOC:** Use the emergency intercom or two-way radio to notify the Network Operations Center (NOC) and Building Security immediately. Declare a "Code Red - Physical Datacenter Hazard".

### 1.2 Emergency Power Off (EPO) Procedures for Affected Racks
When a physical hazard threatens to cause electrical fires or catastrophic short circuits across multiple systems, power must be cut immediately.



**Execution Steps:**
1. **Rack-Level PDU Shutdown (Preferred):** If it is safe to touch the rack (e.g., a localized AC drip that hasn't reached the power strips), remotely log into the intelligent Power Distribution Units (PDUs) via the management network and issue a power-off command to the affected rack's outlets.
2. **Zone-Level EPO:** If remote access is unavailable and safe physical access is possible, use the localized breaker panel to cut power strictly to the affected row/zone.
3. **Room-Level EPO (The Last Resort):** * **Warning:** Depressing the main room EPO button (usually located at the datacenter exit doors) will instantly drop power to all IT loads, bypassing UPS systems. This will cause a hard crash of the entire datacenter.
   * **When to use:** ONLY press the room-level EPO if there is an active, uncontrollable fire, or if a person is actively being electrocuted and you cannot isolate the circuit. 
4. Once power is confirmed dead, place physical barricades (wet floor signs, caution tape) around the hazard zone.

---

## Chapter 2: Service Isolation & Disaster Recovery

### 2.1 Isolating Affected Hardware (e.g., DNS Servers) from the Network
Once the physical hazard is contained or power is cut, the NOC must logically isolate the dead or dying hardware to prevent network broadcast storms, routing loops, or corrupted data replication.

**Execution Steps (NOC / Network Engineering):**
1. **Identify the Affected IPs/MACs:** Pull the CMDB records for the hardware located in the damaged rack (e.g., Core DNS Server 01).
2. **Port Shutdown:** Log into the Top-of-Rack (ToR) or End-of-Row (EoR) aggregation switches.
   * Command (Cisco OS): `interface range [affected_ports]`, followed by `shutdown`.
3. **Withdraw Routing Announcements:** If the affected server is a critical load balancer or core router, manually withdraw its BGP/OSPF routes so internal traffic stops attempting to reach the dead node.
4. **Update DNS/IPAM:** If the primary internal DNS server is physically damaged, update the DHCP scopes via the IP Address Management (IPAM) tool to point all clients to the secondary/tertiary DNS servers.

### 2.2 Activating Secondary Datacenter Failover / Cloud Redundancy
With the primary hardware isolated, IT Operations must initiate the Business Continuity / Disaster Recovery (BCP/DR) plan to restore services within the defined Recovery Time Objective (RTO).



**Execution Steps:**
1. **Assess Impact:** Determine which Tier 1 applications were hosted on the damaged hardware. 
2. **Initiate Global Server Load Balancing (GSLB) Failover:** * Log into the enterprise DNS routing portal (e.g., F5 DNS, Route53, or Infoblox).
   * Shift the traffic weighting from the primary datacenter (e.g., US-East) to the secondary datacenter or cloud availability zone (e.g., US-West).
3. **Database Promotion:** If the damaged rack contained the active database writer node, instruct the DBA team to force a failover, promoting the passive synchronous replica in the secondary datacenter to the "Active" role.
4. **Monitor Capacity:** Ensure the secondary site has sufficient compute and bandwidth to handle the 100% traffic load without secondary degradation.

---

## Chapter 3: Cross-Functional Coordination

### 3.1 Engaging Facilities Management (Water leaks, HVAC failures)
IT personnel are not authorized to repair building infrastructure. Facilities Management (FM) must be engaged immediately to stop the environmental hazard at its source.

**Execution Steps:**
1. Open an emergency ticket with the Facilities helpdesk and call the on-call building engineer.
2. **For Water Leaks:** FM must shut off the main water supply valves to the roof chillers or affected plumbing lines. Wet-vacs and commercial dehumidifiers must be deployed immediately to prevent condensation on adjacent cold racks.
3. **For HVAC/CRAC Failures:** If a Computer Room Air Conditioning (CRAC) unit fails, ambient temperatures will rise rapidly (thermal runaway). 
   * FM must deploy portable spot-coolers.
   * IT must proactively perform graceful shutdowns of non-essential development/test servers in that zone to reduce the heat load.

### 3.2 Hardware Assessment and Vendor Dispatch (Dell/HP/Cisco)
Once Facilities has declared the area safe and dry, the hardware must be triaged for permanent replacement. **Do not attempt to power on water-damaged servers.**

**Execution Steps:**
1. **Physical Triage:** Datacenter technicians will extract the affected chassis from the rack. Remove hard drives (if dry) for potential forensic recovery.
2. **Compile the Damage List:** Extract the serial numbers/service tags of all ruined equipment.
3. **Initiate RMA / Insurance Claim:** * Contact the OEM (Original Equipment Manufacturer) account representatives. 
   * Note: Standard warranty (e.g., Dell ProSupport) *does not* cover environmental water damage or fire. This must be routed through IT Procurement and Corporate Insurance for emergency replacement hardware (Accidental Damage claims).
4. Request expedited delivery of identical hardware specifications to begin the bare-metal rebuild process.

---

## Chapter 4: Post-Incident Auditing

### 4.1 Creating the Major Problem Record and Post-Mortem
Environmental failures represent catastrophic risks. A thorough Root Cause Analysis (RCA) is mandatory to prevent recurrence.

**Execution Steps:**
1. Create a **Problem Record** in ServiceNow linked to all incident tickets generated during the outage.
2. Schedule a Post-Mortem meeting within 72 hours involving Datacenter Ops, Facilities, Network Engineering, and Major Incident Management.
3. **Define Corrective and Preventive Actions (CAPA):**
   * *Example:* "Facilities to install physical drip pans above Rack Row A."
   * *Example:* "IT Ops to install under-floor water detection sensors wired directly to NOC alerting."
   * *Example:* "Architects to review why the secondary DNS server did not automatically take the load."
4. Close the Problem record only when all CAPA tasks are successfully implemented and tested.

---

## Chapter 5: Previously Solved Incidents

### Incident: INC0000016
* **Symptom:** Numerous users reported "Cannot resolve host" errors and inability to access any internal web applications. A datacenter technician simultaneously called the NOC reporting that severe rain was leaking directly onto the main DNS server rack (Rack 4B) due to a roof membrane failure. The ticket was bouncing between assignment groups.
* **Triage Performed:** The Major Incident Manager intercepted the bouncing ticket (SOP Step 2.1). Visual inspection confirmed water pooling on the active core DNS appliances. 
* **Root Cause:** A severe storm compromised the datacenter roof. The primary DNS servers suffered catastrophic electrical shorts due to water ingress. 
* **Resolution:** 1. The technician performed a localized rack PDU shutdown (SOP Step 1.2) to prevent a wider electrical fire. 
  2. Facilities Management was dispatched to deploy tarps and wet-vacs (SOP Step 3.1).
  3. Network Engineering immediately altered the IPAM DHCP scopes to force all client traffic to the secondary cloud-hosted DNS servers (SOP Step 2.1), restoring enterprise name resolution within 15 minutes.
  4. The ruined hardware was extracted and an emergency procurement request was submitted to Cisco (SOP Step 3.2). 

### Incident: INC0000802
* **Symptom:** NOC monitoring systems triggered critical temperature alarms (exceeding 95°F / 35°C) in Datacenter Zone C.
* **Triage Performed:** On-site personnel investigated and found the primary CRAC (AC) unit for Zone C had a blown compressor belt.
* **Root Cause:** Mechanical failure of the HVAC system leading to rapid thermal runaway.
* **Resolution:** Engaged Facilities Management who deployed two emergency spot-coolers to the aisle (SOP Step 3.1). To prevent hardware damage, the virtualization team executed a vMotion script to migrate all critical Tier-1 VMs to host servers in Zone A. Non-essential Dev/QA servers in Zone C were gracefully shut down to lower the thermal footprint (SOP Step 3.1) until the CRAC belt was replaced 4 hours later.