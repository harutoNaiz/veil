# Enabling Veil Guard signals on the iQOO (restricted settings)

A sideloaded app cannot be enabled as an accessibility service until Android's "restricted settings" is allowed for it.

1. Install the Guard debug APK.
2. Settings -> Apps -> App management -> **Veil Guard** (App info).
3. Tap the three-dot menu (top right) -> **Allow restricted settings**. Confirm with your PIN. (The menu appears only after a first failed attempt to enable the service: if it is missing, do step 4 once, then come back.)
4. Settings -> Accessibility (More settings) -> Installed/Downloaded services -> **Veil Guard signals** -> switch on -> Allow.
5. Check: `adb logcat -s VeilSignals` after a log start, or run `tools\verify\4.2.1.ps1 -Phone`.

Screenshots (to add on the phone):

- [ ] App info with the three-dot menu open
- [ ] "Allow restricted settings" confirmation
- [ ] Accessibility service list with Veil Guard signals
- [ ] Service enabled prompt
