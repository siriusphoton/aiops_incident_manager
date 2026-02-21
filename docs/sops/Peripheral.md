# SOP 06: Peripheral & Hardware Triage

**Target Incidents:** Missing `cmdb_ci` data in hardware tickets, computers not detecting peripherals (headphones, monitors, mice), and audio device failures.
**Document Owner:** IT Operations / End User Computing (EUC)
**Last Updated:** February 2026

---

## Chapter 1: Hardware Diagnostics Workflow

### 1.1 Identifying the Asset (CMDB_CI validation)
Effective hardware troubleshooting and ITIL Incident Management cannot proceed without identifying the exact physical asset experiencing the failure. In ServiceNow, this is recorded in the `cmdb_ci` (Configuration Item) field. 

**The Missing Context Problem:**
When users submit tickets stating "my computer is broken" or "my headphones aren't working" via email, the `cmdb_ci` field is often blank. L1 agents must enforce data hygiene before attempting remote diagnostics.

**Execution Steps for L1 Triage:**
1. **Check the Ticket:** Look at the `cmdb_ci` field. If it is populated (e.g., `LT-US-98765`), proceed to Step 3.
2. **Pushback for Asset Tag:** If the field is empty, the agent (or AI) must set the ticket state to "On Hold - Awaiting Caller" and request the asset tag:
   * *"To diagnose your hardware issue securely and accurately, please provide the Asset Tag or Service Tag of your machine. This is typically found on a barcode sticker on the bottom of your laptop or the back of your desktop."*
3. **Cross-Reference in ServiceNow:** Once the tag is provided, search the `cmdb_ci_computer` table to verify the machine's model, warranty status, and assigned user. Update the incident record to link the CI.

### 1.2 Wired vs. Bluetooth vs. Docking Station peripherals
Peripherals fail for different reasons depending on their connectivity method. Establishing the connection path is the first step in root-cause isolation.



* **Wired Peripherals (USB-A / USB-C / 3.5mm Jack):**
  * *Triage:* Is the device plugged directly into the laptop chassis, or is it routed through a USB hub or monitor?
  * *Action:* Always instruct the user to plug the device *directly* into the laptop's motherboard ports to rule out hub failures. For 3.5mm jacks, ensure no dust or debris is blocking the physical contacts.
* **Bluetooth Peripherals:**
  * *Triage:* Bluetooth issues are often caused by OS-level pairing state desynchronization or local 2.4GHz interference.
  * *Action:* Instruct the user to "Forget" the device in Windows Settings > Bluetooth & Devices, put the headset back into pairing mode, and re-pair. Check battery levels.
* **Docking Stations (Thunderbolt / USB-C):**
  * *Triage:* Docks act as middle-men. If a headset plugged into a dock fails, but works when plugged into the laptop, the dock is the point of failure.
  * *Action:* Docking stations require dedicated firmware (e.g., Dell WD19TB firmware). Power cycle the dock by unplugging its AC adapter for 15 seconds, then reconnecting.

---

## Chapter 2: OS-Level Troubleshooting

### 2.1 Windows Device Manager Error Codes (Code 10, Code 43)
Windows provides specific error codes when a hardware device fails to initialize. These codes dictate your next troubleshooting steps.



**Diagnostic Steps:**
1. Instruct the user to press `Win + X` and select **Device Manager**.
2. Expand the **Audio inputs and outputs**, **Sound, video and game controllers**, or **Universal Serial Bus controllers** categories.
3. Look for devices with a **Yellow Warning Triangle**. Right-click the device and select **Properties**.
4. Read the "Device status" box on the General tab:
   * **Code 10 ("This device cannot start"):** This almost always indicates a corrupted or incorrect driver. Proceed to SOP Step 2.2.
   * **Code 43 ("Windows has stopped this device because it has reported problems"):** The hardware has sent a fatal fault signal to the OS. This often indicates a physical hardware failure (frayed cable, dead USB port) or severely outdated firmware.

### 2.2 Updating, Rolling Back, and Reinstalling Audio/USB Drivers
If the OS recognizes the device but it fails to operate (e.g., Code 10), the driver stack must be rebuilt.

**Execution Steps:**
1. **Roll Back the Driver:** If the issue started immediately after a Windows Update, the new driver may be flawed.
   * Right-click the device in Device Manager > **Properties** > **Driver** tab > **Roll Back Driver**.
2. **Uninstall and Reinstall (Clean Sweep):**
   * Right-click the device > **Uninstall device**. 
   * *Critical:* If prompted, check the box that says "Attempt to remove the driver software for this device."
   * Click the **"Scan for hardware changes"** icon (blue monitor with a magnifying glass) in the top toolbar. Windows will redetect the device and pull a fresh generic driver from the local repository.
3. **OEM Driver Updates:** For stubborn audio issues (e.g., Realtek High Definition Audio), generic Windows drivers often fail. Launch the OEM update utility (Dell Command | Update, Lenovo Commercial Vantage, or HP Support Assistant) to pull the manufacturer-approved audio driver.

### 2.3 Restarting Windows Audio Services
If Device Manager shows no errors, but the user has a red "X" over their speaker icon in the system tray, the underlying Windows background services may have crashed.

**Execution Steps:**
1. Press `Win + R`, type `services.msc`, and press Enter.
2. Locate the following two services:
   * **Windows Audio**
   * **Windows Audio Endpoint Builder**
3. Right-click **Windows Audio** and select **Restart**. (This will automatically restart the Endpoint Builder as well).
4. Verify the "Startup Type" for both services is set to **Automatic**.
5. Test the audio output by clicking the speaker icon in the taskbar and adjusting the volume slider to generate the Windows chime.

---

## Chapter 3: Hardware Replacement Logistics

### 3.1 Warranty Validation Check
If all OS-level troubleshooting fails, the hardware is likely physically defective. Before ordering replacement parts or a new machine, L2 agents must check the warranty status.

**Execution Steps:**
1. Retrieve the machine's Service Tag / Serial Number from the `cmdb_ci` record in ServiceNow.
2. Navigate to the appropriate vendor portal (e.g., `https://www.dell.com/support/` or `https://pcsupport.lenovo.com/`).
3. Enter the Service Tag and review the Entitlement status.
4. **Action:**
   * If **In-Warranty (ProSupport/Premium):** Open a dispatch ticket directly with the vendor for a motherboard or port replacement. Log the vendor's dispatch reference number in the ServiceNow incident.
   * If **Out-of-Warranty:** Proceed to Step 3.2 to initiate internal IT procurement.

### 3.2 Initiating the Hardware Procurement/Replacement Workflow
Replacing out-of-warranty or lost peripherals (like headsets or mice) follows the internal IT catalog workflow.

**Execution Steps:**
1. Instruct the user to navigate to the IT Self-Service Portal.
2. Direct them to the **Hardware Catalog** > **Peripherals**.
3. Have the user add the standard enterprise-approved headset (e.g., Jabra Evolve2 65 or Poly Voyager) to their cart.
4. The catalog item will automatically route to the user's line manager for budget approval.
5. Once the catalog item (RITM) is generated, close the original troubleshooting Incident with the note: *"Hardware deemed defective. Troubleshooting exhausted. User directed to catalog for replacement under RITMXXXXXXX."*

---

## Chapter 4: Previously Solved Incidents

### Incident: INC0009002
* **Symptom:** User stated, "My computer is not detecting the headphone device." The ticket had no CMDB_CI attached.
* **Triage Performed:** L1 Agent requested the asset tag. User provided `LT-US-55412`. Screen-share revealed the user was plugging a 3.5mm headset into a Dell WD19 Thunderbolt Dock. 
* **Root Cause:** Device Manager showed a yellow warning triangle (Code 43) over the "Realtek USB Audio" interface, which is the internal DAC (Digital-to-Analog Converter) for the docking station. The dock's audio chipset had crashed.
* **Resolution:** Agent power-cycled the docking station by removing the AC power adapter for 15 seconds (SOP Step 1.2). Upon reconnection, the dock re-initialized, Windows re-detected the Realtek USB Audio device without errors, and the headset began outputting sound.

### Incident: INC0000026
* **Symptom:** User reported their Bluetooth headset kept dropping calls and disconnecting randomly during Teams meetings. 
* **Triage Performed:** Checked Device Manager; no errors on the Intel Wireless Bluetooth adapter. Unpaired and re-paired the headset, but drops continued. Checked the OEM update utility.
* **Root Cause:** The laptop's BIOS and Bluetooth radio firmware were severely outdated (over 18 months old), causing power-management conflicts with the newer Bluetooth 5.0 headset protocol.
* **Resolution:** Executed Dell Command | Update (SOP Step 2.2). Pushed the latest BIOS payload and Intel Bluetooth driver updates. Restarted the machine. The headset maintained a stable connection post-update.