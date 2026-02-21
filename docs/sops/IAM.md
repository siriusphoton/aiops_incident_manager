# SOP 08: Identity & Access Management (IAM) and Security Lockouts

**Target Incidents:** General IT: Forgotten passwords, MFA resets, locked accounts, and suspected account compromises.
**Document Owner:** IT Operations / Identity & Access Management (IAM) Team
**Last Updated:** February 2026

---

## Chapter 1: Identity Lifecycle and Verification

### 1.1 Caller Identity Verification Protocols (Security Questions/Manager Approval)
The Service Desk is the primary target for social engineering attacks (e.g., vishing). Malicious actors frequently pose as executives or remote employees to trick L1 agents into resetting passwords or altering Multi-Factor Authentication (MFA) devices. **Strict adherence to identity verification protocols is mandatory. No exceptions.**

**Tiered Verification Protocol:**
Before resetting a password, unlocking an account, or modifying an MFA token, the agent must successfully verify the caller's identity using one of the following approved methods:

1. **Self-Service Verification (Preferred):** The user authenticates to the IT portal using their smart card or biometric login (if available) and submits the ticket securely.
2. **Standard Knowledge-Based Authentication (KBA):** The agent must ask the user to confirm three (3) data points from their HR profile that are not publicly available on LinkedIn or corporate directories.
   * Employee ID number.
   * Date of Hire.
   * Last four digits of their government-issued ID or SSN (if stored in the secure IAM vault).
3. **Manager Call-Back (For High-Privilege Accounts):** If the user is an Executive, VIP, or System Administrator, KBA is insufficient. The agent must:
   * End the call with the user.
   * Look up the user's direct line manager in Active Directory.
   * Call the manager on their registered corporate number or send a secure Teams message to authorize the reset.
4. **Video Verification (If KBA Fails):** If a user cannot remember their security answers or is a new hire, the agent must initiate a brief Teams or Zoom video call to visually match the user's face to their corporate ID badge or government ID.

---

## Chapter 2: Password Reset Workflows

### 2.1 Directing Users to Self-Service Password Reset (SSPR)
To reduce IT overhead and maintain a strict audit trail, users should always be directed to the automated Self-Service Password Reset (SSPR) portal before manual intervention is attempted.

**Execution Steps:**
1. Instruct the user to navigate to `passwordreset.microsoftonline.com` (or the enterprise equivalent) on an alternative device (e.g., their personal smartphone).
2. The user will be prompted to enter their corporate email address and complete a CAPTCHA.
3. SSPR will challenge the user using their pre-registered secondary methods:
   * SMS Text Message code.
   * Alternate personal email address.
   * Authenticator App push notification.
4. Once verified, the user will be prompted to create a new password. Remind the user of the current **Enterprise Password Complexity Rules**:
   * Minimum 14 characters.
   * Must contain uppercase, lowercase, numbers, and special characters.
   * Cannot match the last 10 passwords.
   * Cannot contain the user's name or the company name.

### 2.2 Manual Active Directory Force-Resets
If SSPR is broken, the user is locked out of all devices, or the user is a new hire who hasn't registered for SSPR, L1/L2 agents must perform a manual reset via Active Directory.



**Execution Steps:**
1. Open **Active Directory Users and Computers (ADUC)** or the enterprise IAM administrative web console.
2. Search for the user by their `sAMAccountName` or Employee ID.
3. Right-click the user object and select **Reset Password**.
4. Generate a complex, random temporary password (e.g., using a password generator). Do not use predictable patterns like `Welcome2026!`.
5. **Critical Checkboxes:**
   * Check: **User must change password at next logon**. (This ensures the temporary password is immediately rotated by the user).
   * Check: **Unlock the user's account**. (If the account was locked due to bad attempts).
6. Click **OK**.
7. Communicate the temporary password to the user securely (verbally over the phone, or via an encrypted SMS tool). Never email a password to a user's alternate email address without encryption.
8. Ask the user to attempt a login while on the phone to confirm they are prompted to set a new, permanent password.

---

## Chapter 3: Multi-Factor Authentication (MFA) Recovery

### 3.1 Clearing Old MFA Tokens in Entra ID / Okta
A common scenario is a user upgrading their mobile phone, dropping their old phone in water, or accidentally deleting the Authenticator app. Because the MFA token is bound to the physical hardware chip of the old device, the user will be permanently locked out until IT clears the old association.



**Execution Steps (Microsoft Entra ID Example):**
1. Ensure the user's identity has been verified via Manager Call-Back or Video Verification (SOP Step 1.1).
2. Log into the **Microsoft Entra admin center** (formerly Azure AD).
3. Navigate to **Users** > **All users** and search for the affected user.
4. Select the user and click on **Authentication methods** in the left-hand navigation pane.
5. You will see a list of registered methods (e.g., Microsoft Authenticator, Phone number).
6. Click the three dots (`...`) next to the old Microsoft Authenticator instance and select **Delete**.
7. Click **Require re-register MFA**. This flushes the cached token and forces the system to prompt the user to set up MFA from scratch on their next login.

### 3.2 Re-registering New Mobile Devices for Authenticator Apps
Once the old tokens are cleared, the user must securely register their new device.

**Execution Steps:**
1. Instruct the user to download the approved Authenticator app (Microsoft Authenticator, Duo Mobile, or Okta Verify) from the iOS App Store or Google Play Store.
2. If the enterprise uses **Temporary Access Passes (TAP)**:
   * In Entra ID, click **Add authentication method** > **Temporary Access Pass**.
   * Set the duration to 1 hour and generate the pass.
   * Provide the TAP code to the user.
3. Direct the user to `mysignins.microsoft.com/security-info` (or the equivalent Okta dashboard) on their computer.
4. They will log in using their password and the TAP code (bypassing the need for the broken MFA app).
5. The portal will display a QR code.
6. Instruct the user to open the Authenticator app on their new phone, click "+" or "Add Account" > "Work or School Account", and scan the QR code.
7. Send a test push notification to verify successful binding.

---

## Chapter 4: Compromised Account Containment

### 4.1 Identifying "Impossible Travel" or Suspicious Lockout Patterns
Active Directory lockouts aren't always user error; they are frequently indicators of an active cyber attack. Service Desk agents are the first line of defense in identifying these anomalies.

**Red Flags for Investigation:**
* **Continuous Lockouts:** The user's account locks out every 15 minutes, even after they reset their password and turn off all their mobile devices. This indicates a cached credential is hammering the server, or a brute-force attack is underway.
* **Impossible Travel:** The user is on the phone with you in New York, but Azure AD Sign-in logs show failed login attempts originating from an IP address in Russia or Nigeria just 5 minutes ago.
* **Password Spraying:** Multiple users across the organization report lockouts simultaneously, indicating an attacker is systematically trying the same weak password against the entire corporate directory.

**Diagnostic Steps:**
1. Open the user's profile in Azure AD/Entra ID and view the **Sign-in logs**.
2. Filter for "Status: Failure".
3. Check the "Location" and "IP Address" columns.
4. Ask the user: *"Are you currently using a VPN routed through [Country Name]?"* If they answer no, the account is under attack.

### 4.2 Freezing Accounts and Engaging SecOps
If an account compromise is suspected (e.g., Impossible Travel is confirmed, or the user admits they clicked a phishing link and entered their password), immediate containment is required.

**Emergency Containment Workflow:**
1. **Disable the Account:** In ADUC, right-click the user and select **Disable Account**. (This is safer than a password reset, as it instantly halts all authentication attempts).
2. **Revoke Active Sessions:** In Entra ID, navigate to the user's profile and click **Revoke sessions**. This invalidates all active OAuth tokens, instantly kicking the attacker out of Exchange Online, SharePoint, and Teams.
   * *PowerShell Equivalent:* `Revoke-AzureADUserAllRefreshToken -ObjectId <UserPrincipalName>`
3. **Engage Security Operations (SecOps):**
   * Do not unlock the account.
   * Create a High Priority incident ticket assigned directly to the **Cyber Security / SOC** queue.
   * Prefix the ticket title: `URGENT - SUSPECTED COMPROMISE - [Username]`.
   * Include the suspicious IP addresses, locations, and timeframes found in the sign-in logs.
4. Inform the user: *"We have detected unauthorized access attempts on your account. For your protection, I have frozen your access and escalated this to the Security Operations Center. They will contact you shortly to perform a forensic review before access can be restored."*

---

## Chapter 5: Previously Solved Incidents

### Incident: INC0000291
* **Symptom:** User called the Service Desk extremely frustrated. They stated: "My account locks out exactly 10 minutes after you unlock it. I have reset my password three times today."
* **Triage Performed:** Verified the user's identity. Checked the Active Directory Domain Controller Security Event Logs (Event ID 4740 - User Account Locked Out). The logs indicated the lockout was originating from a specific IP address on the internal Wi-Fi network.
* **Root Cause:** The user had an old, personal iPad tucked in their briefcase. The iPad was connected to the corporate Wi-Fi and the native Apple Mail app was constantly trying to sync their corporate Exchange mailbox using an old password from three months ago. After 5 failed attempts, the Active Directory lockout policy was triggered, locking the user's overarching account.
* **Resolution:** Instructed the user to locate the iPad, put it in Airplane Mode, and update the password in the Settings > Mail > Accounts menu. Unlocked the AD account. The continuous lockouts ceased immediately.

### Incident: INC0000405
* **Symptom:** User called requesting an MFA reset. They stated they received a new phone and couldn't log into the VPN. 
* **Triage Performed:** Agent attempted standard KBA verification (SOP Step 1.1). The caller failed to provide their correct Date of Hire and hesitated on their Employee ID. The agent initiated a Manager Call-Back. The manager stated the user was currently on an international flight without internet access and could not possibly be calling the helpdesk.
* **Root Cause:** A malicious actor was performing a sophisticated vishing (voice phishing) attack, attempting to execute an MFA bypass (SIM swap / device hijacking) by tricking the Service Desk into binding a new Authenticator app to the attacker's device.
* **Resolution:** The agent immediately denied the request, disabled the AD account (SOP Step 4.2), and escalated to the SOC. The SOC initiated a company-wide alert for social engineering attempts. The actual user's account remained secure.