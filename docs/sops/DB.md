# SOP 05: Enterprise Database Installation & Maintenance

**Target Incidents:** Requests for Oracle 10GR2 / Database installations and setups.
**Document Owner:** IT Operations / Database Administration (DBA) Team
**Last Updated:** February 2026

---

## Chapter 1: Prerequisites & Compliance

### 1.1 Verifying Licensing and Approved Software Lists
Enterprise database software, particularly Oracle, operates under strict and highly audited licensing models. Installing an unapproved instance can expose the enterprise to millions of dollars in compliance penalties. 

**Pre-Installation Validation Steps:**
1. **Check the Software Asset Management (SAM) Database:** Verify that the enterprise has an available license for the specific version requested (e.g., Oracle 10g Release 2 / 10.2.0.1). Note whether the license is per-processor, per-core, or Named User Plus (NUP).
2. **Review ITSM Approvals:** Ensure the installation request contains explicit, documented approval from both the Department Head (budget owner) and the IT Procurement/SAM team.
3. **Verify Enterprise Architecture (EA) Alignment:** Legacy versions like Oracle 10GR2 are generally deprecated. The L1/L2 agent must confirm if there is an EA exception on file permitting the installation of legacy databases for specific backward-compatible applications.
4. **Action:** If compliance checks fail, set the incident to "On Hold - Awaiting Caller" and reply: *"Database installations require explicit licensing clearance. Please attach the approved Software Procurement form and Architecture Exception waiver to proceed."*

### 1.2 Hardware & OS Prerequisite Checks (Memory, Swap space)
Oracle databases require specific OS-level configurations to function correctly. Failure to meet these will cause the Oracle Universal Installer (OUI) to fail or result in unstable database instances.



**Execution Steps (Linux/UNIX Environments):**
1. **Memory (RAM) Check:** Ensure the server has a minimum of 1GB RAM (2GB+ recommended for production).
   * Command: `grep MemTotal /proc/meminfo`
2. **Swap Space Validation:** Oracle requires swap space directly proportional to the available RAM (typically 1.5x RAM if RAM is between 1GB-2GB, or equal to RAM if >2GB).
   * Command: `grep SwapTotal /proc/meminfo`
3. **Kernel Parameters:** The OS kernel must be tuned to allocate shared memory properly.
   * Edit `/etc/sysctl.conf` to configure `kernel.shmall`, `kernel.shmmax`, and `fs.file-max`.
   * Apply changes using `sysctl -p`.
4. **Dedicated User Account:** Create the `oracle` OS user and assign it to the `oinstall` (inventory) and `dba` (database administration) groups.
   * Command: `useradd -g oinstall -G dba oracle`

---

## Chapter 2: Execution of Database Installers

### 2.1 Running the Oracle Universal Installer (OUI)
The Oracle Universal Installer is a Java-based GUI tool used to install the database software binaries. 

**Execution Steps:**
1. Switch to the `oracle` user: `su - oracle`.
2. Ensure the X11 display is properly routed to your local machine (if installing remotely). 
   * Command: `export DISPLAY=<your_local_ip>:0.0`
3. Navigate to the directory containing the unzipped Oracle installation media.
4. Execute the installer: `./runInstaller`
5. **OUI GUI Walkthrough:**
   * **Inventory Directory:** Set to `/u01/app/oraInventory` (ensure `oinstall` group has write permissions).
   * **Installation Type:** Select "Enterprise Edition".
   * **Oracle Home Location:** Define the path where the binaries will reside (e.g., `/u01/app/oracle/product/10.2.0/db_1`).
   * **Prerequisite Checks:** The OUI will perform a final check. Resolve any "Failed" warnings before clicking "Next".
6. **Root Scripts:** At the end of the installation, OUI will prompt you to run two scripts as the `root` user (`orainstRoot.sh` and `root.sh`). Open a separate terminal, switch to `root`, execute them, and return to the OUI to click "OK".

### 2.2 Setting Environment Variables (`ORACLE_HOME`, `ORACLE_SID`)
For the OS to recognize Oracle commands (like `sqlplus`), the `oracle` user's profile must be configured with specific environment variables.

**Execution Steps:**
1. Open the user profile file for editing (e.g., `vi ~/.bash_profile`).
2. Append the following lines, adjusting the paths to match your installation:
   ```bash
   export ORACLE_BASE=/u01/app/oracle
   export ORACLE_HOME=$ORACLE_BASE/product/10.2.0/db_1
   export ORACLE_SID=ORCL  # Replace ORCL with your target database name
   export PATH=$ORACLE_HOME/bin:$PATH

```

3. Save the file and apply the changes to the current session: `source ~/.bash_profile`.
4. Verify by running `echo $ORACLE_HOME`.


## Chapter 3: Post-Installation Configurations

### 3.1 Configuring the Network Listener (`listener.ora`)

The Oracle Listener is a dedicated background process that listens for incoming client connection requests and manages traffic to the database instance.

**Execution Steps:**

1. Launch the Oracle Net Configuration Assistant by typing `netca` in the terminal.
2. Select **Listener configuration** > **Add**.
3. Name the listener (default is usually `LISTENER`).
4. Select the protocol (TCP is standard).
5. Specify the port (default is `1521`).
6. Finish the wizard. This automatically generates the `/u01/app/oracle/product/10.2.0/db_1/network/admin/listener.ora` file.
7. Start the listener via command line: `lsnrctl start`.
8. Check the status to ensure it is running: `lsnrctl status`.

### 3.2 Initializing the Default Database Schema

Once the software binaries are installed and the listener is active, the actual database (datafiles, control files, redo logs) must be created.

**Execution Steps:**

1. Launch the Database Configuration Assistant by typing `dbca` in the terminal.
2. Select **Create a Database**.
3. Choose a template (e.g., "General Purpose").
4. Enter the **Global Database Name** and **SID** (e.g., `ORCL`).
5. Configure management options (Enable Enterprise Manager if required by the DBA team).
6. Set administrative passwords for the `SYS` and `SYSTEM` superuser accounts. Store these securely in the enterprise password vault (e.g., CyberArk).
7. Review the storage configurations and click **Finish** to begin the database creation process.

---

## Chapter 4: Common Installation Errors & Rollbacks

### 4.1 Resolving Java Runtime Conflicts

Because OUI and DBCA are Java-based, GUI rendering failures are the most common installation roadblocks.

* **Symptom:** Running `./runInstaller` results in an immediate crash or an error stating: `Exception in thread "main" java.lang.UnsatisfiedLinkError`.
* **Root Cause:** Incompatibility between the bundled legacy Java Runtime Environment (JRE) in Oracle 10g and modern 64-bit Linux OS libraries.
* **Resolution Steps:**
1. Ensure 32-bit compatibility libraries are installed on the OS (`glibc.i686`, `libXext.i686`, `libXtst.i686`).
2. If the X11 display is failing, ensure `xhost +` has been run on the client machine, and verify the `$DISPLAY` variable is correctly formatted.
3. Bypass the bundled JRE by passing a modern JRE to the installer: `./runInstaller -jreLoc /usr/lib/jvm/jre-1.8.0`



### 4.2 Complete Uninstallation and Cleanup Procedures

If an installation corrupts halfway through, you cannot simply rerun the installer. You must perform a manual, clean scrub of the failed Oracle footprint.

**Execution Steps (Use with extreme caution):**

1. Stop all Oracle processes (Listener, Database instances).
2. Delete the Oracle Home directory: `rm -rf /u01/app/oracle/product/10.2.0/db_1`
3. Delete the Oracle Inventory directory: `rm -rf /u01/app/oraInventory`
4. Remove the global Oracle pointer files (Must be root):
* `rm /etc/oraInst.loc`
* `rm /etc/oratab`


5. Remove the temporary installation files: `rm -rf /tmp/OraInstall*`
6. You are now cleared to attempt a fresh installation.

---

## Chapter 5: Previously Solved Incidents

### Incident: INC0000010

* **Symptom:** A developer submitted a ticket stating: "Need Oracle 10GR2 installed on Dev Server 4."
* **Triage Performed:** The request lacked SAM approval. Oracle 10GR2 is a legacy product and normally blocked by Enterprise Architecture policies.
* **Root Cause:** Standard software request pipeline bypassed.
* **Resolution:** Placed ticket "On Hold". Engaged the developer's manager who provided an EA waiver confirming the legacy database was required for backward-compatibility testing of an old financial module. Once the license was verified in the SAM portal, the DBA team executed the installation utilizing the `runInstaller` silent mode.

### Incident: INC0000145

* **Symptom:** During an approved Oracle installation, the L2 engineer reported the Database Configuration Assistant (`dbca`) hung at 85% completion.
* **Triage Performed:** Reviewed the OS performance metrics during the hang. Noticed that physical memory was at 99% and Swap utilization was at 100%.
* **Root Cause:** The VM was provisioned with 2GB of RAM but 0GB of Swap space, violating the Oracle prerequisite ratios (SOP Step 1.2). When DBCA attempted to initialize the System Global Area (SGA), the Linux OOM (Out of Memory) killer terminated the background Java processes.
* **Resolution:** Scrubbed the failed installation (SOP Step 4.2). Shut down the VM, increased RAM to 4GB, and allocated a 4GB Swap partition. Reran the installation successfully.
