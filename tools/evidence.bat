@echo off
rem Collect post-crash evidence from the phone. No root required for most of it.
rem Run right after the phone comes back up from the black-screen reboot.
setlocal
set ADB=%~dp0..\toolchain\android-sdk\platform-tools\adb.exe

rem timestamp via PowerShell (locale-proof; %date% substrings differ by locale)
set TS=%date%
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%I
set OUT=%~dp0..\evidence\%TS%
mkdir "%OUT%" 2>nul

echo writing to %OUT%
%ADB% devices -l > "%OUT%\00_devices.txt" 2>&1

rem ---- what we came for: why did the phone restart? ------------------------
%ADB% shell getprop > "%OUT%\01_getprop.txt" 2>&1
%ADB% shell getprop ro.boot.bootreason > "%OUT%\02_bootreason.txt" 2>&1
%ADB% shell getprop sys.boot.reason >> "%OUT%\02_bootreason.txt" 2>&1
%ADB% shell getprop ro.boot.bootkeys >> "%OUT%\02_bootreason.txt" 2>&1
%ADB% shell uptime >> "%OUT%\02_bootreason.txt" 2>&1

rem ---- dropbox survives reboots; it holds the panic/restart records ---------
rem SYSTEM_LAST_KMSG = kernel log of the crashed boot (best case)
rem SYSTEM_RESTART   = who asked for the restart
rem SYSTEM_BOOT      = boot times
%ADB% shell dumpsys dropbox --print SYSTEM_LAST_KMSG > "%OUT%\03_dropbox_last_kmsg.txt" 2>&1
%ADB% shell dumpsys dropbox --print SYSTEM_RESTART > "%OUT%\04_dropbox_restart.txt" 2>&1
%ADB% shell dumpsys dropbox --print SYSTEM_BOOT > "%OUT%\05_dropbox_boot.txt" 2>&1
%ADB% shell dumpsys dropbox --print SYSTEM_TOMBSTONE >> "%OUT%\05_dropbox_boot.txt" 2>&1
%ADB% shell dumpsys dropbox --print > "%OUT%\06_dropbox_all.txt" 2>&1

rem ---- DFRoot's own chain: which /dev marker survived this boot -------------
%ADB% shell ls -l /dev/df /dev/dfm0 /dev/dfm1 /dev/dfm2 /dev/dfm3 /dev/dfm4 /dev/dfm5 /dev/dfm6 /dev/dfme0 /dev/dfme1 /dev/dfme2 /dev/dfmw0 /dev/dfmw1 > "%OUT%\07_dev_markers.txt" 2>&1

rem ---- logs of the CURRENT boot (a kernel panic clears these) ---------------
%ADB% logcat -b all -d -v time > "%OUT%\08_logcat_all.txt" 2>&1
%ADB% shell dmesg > "%OUT%\09_dmesg.txt" 2>&1

rem ---- root-only sources: these will fail on a non-rooted phone ------------
rem They are here so that a run made right after a successful root also works.
%ADB% shell ls -l /sys/fs/pstore > "%OUT%\10_pstore_list.txt" 2>&1
%ADB% shell cat /sys/fs/pstore/console-ramoops-0 > "%OUT%\11_pstore_console.txt" 2>&1
%ADB% shell "ls -l /data/log | grep -i dumpstate" > "%OUT%\12_samsung_dumpstate_logs.txt" 2>&1
rem run-as only works for debuggable apps, so this normally fails; use the on-screen
rem DFRoot menu -> "Run log" instead
%ADB% exec-out run-as df.root cat /data/user_de/0/df.root/files/diag.log > "%OUT%\13_dfroot_diaglog_runas.txt" 2>&1
rem /proc/kallsyms is denied to the shell domain by SELinux on this device;
rem try anyway so the file records that it was attempted
%ADB% shell "grep -c . /proc/kallsyms" > "%OUT%\14_kallsyms_attempt.txt" 2>&1

echo.
echo done. Send me the whole folder: %OUT%
echo Also open DFRoot in the phone, menu -^> "Run log" and screenshot it.
pause
