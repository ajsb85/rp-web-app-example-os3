# Findings & Investigation Log

This document records the full investigation, in chronological order, from first contact with the board through to a successfully built and deployed web app. It's written so the failure modes and fixes are reproducible and searchable — several of these were not obvious from Red Pitaya's official documentation.

## Environment

- Board: Red Pitaya STEMlab 125-10 (V1r1), reachable at `192.168.68.108` / `rp-f0733a.local`
- OS image: [`RedPitaya_OS_3.00-57_stable.img.zip`](https://downloads.redpitaya.com/downloads/Unify/RedPitaya_OS_3.00-57_stable.img.zip)
- Example app: [`RP_WEB_app_example_2.0.zip`](https://downloads.redpitaya.com/doc/Examples/RP_WEB_app_example_2.0.zip) (targets the older OS 2.0 SDK)

## 1. Initial connectivity

The board was reachable at `192.168.68.108` (ping, SSH port 22 open). A second address on the same network, `192.168.68.1`, turned out to be the router/gateway, not the board — worth double-checking when a network has multiple candidate IPs.

Port 8900 (sometimes associated with Red Pitaya web apps in older documentation/forum posts) was **not** the web UI port on this board/OS — the actual web interface is served on port **80** via nginx.

SSH login uses the documented default credentials: `root` / `root`.

### Non-interactive SSH from a scripted environment

Standard `ssh`/`scp` password auth expects an interactive TTY (or `ssh-askpass`), neither of which is available in a headless scripted shell. `sshpass` and `expect` were not installed and there was no `sudo` access to install them. Worked around this with a small Python helper using `pty.fork()` to allocate a pseudo-terminal, watch the output stream for a `password:` prompt, and inject the password — see `scripts/ssh_rp.py` / `scripts/scp_rp.py` in this repo for the exact approach.

## 2. Re-flashing to OS 3.00-57: the Rufus trap

After flashing `RedPitaya_OS_3.00-57_stable.img.zip` with **Rufus** and rebooting, the board came up in a broken state:

- Port 80: nginx running, but returned **HTTP 500 Internal Server Error**
- Port 22 (SSH): closed — no `sshd` running at all
- Ports 443, 8900: closed

This is the signature of a **partial/corrupted flash**, not a slow boot. The root cause: Rufus's default **"ISO Image mode"** does not correctly handle the multi-partition raw disk layout that Red Pitaya's `.img` uses (boot partition + root filesystem + overlay partitions). It writes something bootable enough to start U-Boot/the kernel and a minimal nginx stub, but the actual root filesystem/application layer and `sshd` never come up correctly.

**Fix:** re-flash using one of:
- [balenaEtcher](https://etcher.balena.io/) (Red Pitaya's documented tool), or
- Rufus, but explicitly selecting **"Write in DD Image mode"** when prompted (not the default ISO mode)

After re-flashing correctly and power-cycling, the board came up clean:

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/root       6.4G  2.4G  3.7G  40% /
```

```
##############################################################################
# Red Pitaya GNU/Linux Ecosystem
# Version: 3.00-e00665135
# Build: 57
# Branch: origin/master
# U-Boot: redpitaya-v2026.1
# Linux Kernel: Release_2026.1
##############################################################################
```

Port 80 → HTTP 200, port 22 → open.

### SSH host key change after re-flash

Reconnecting after the re-flash triggered:

```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
```

This is **expected** — the board generated a new SSH host key as part of the fresh OS image, it is not evidence of a MITM attack. Resolved by removing the stale entry (`ssh-keygen -R <ip>`) and reconnecting to trust the new key.

## 3. Filesystem layout: `/opt/redpitaya` is read-only by default

`/etc/fstab` on this OS build:

```
/dev/mmcblk0p2  /               ext4    errors=remount-ro      0       1
/dev/mmcblk0p1  /boot           vfat    defaults,ro             0       0
/dev/mmcblk0p1  /opt/redpitaya  vfat    defaults,ro             0       2
```

`/` (root, ext4) is read-write. But `/opt/redpitaya` — where web apps live, under `/opt/redpitaya/www/apps/` — is the **same partition as `/boot`** (`mmcblk0p1`, FAT32), mounted **read-only**. Any attempt to copy files there fails with `Read-only file system`.

**Fix:** remount read-write before deploying, and remount back to read-only afterward:

```sh
mount -o remount,rw /opt/redpitaya
# ... copy files, build ...
mount -o remount,ro /opt/redpitaya
```

## 4. `scp` fails with "stat remote: No such file or directory"

Modern OpenSSH (9.0+) clients default `scp` to the SFTP protocol. This board's `sshd` does not ship an `sftp-server` binary, so any SFTP-based transfer fails immediately with a misleading `stat remote: No such file or directory` error — it looks like a missing destination path, but the destination is never actually consulted.

**Fix:** force the legacy SCP protocol explicitly:

```sh
scp -O -r <src> root@<host>:<dst>
```

## 5. Build failures: SDK/toolchain drift between OS 2.0 and OS 3.00

The example app was written against the OS 2.0 SDK. Building it unmodified against the OS 3.00 SDK (`/opt/redpitaya/include`, `/opt/redpitaya/rp_sdk`) fails in three distinct ways, each masking the next:

### 5a. `std::is_same_v` / `if constexpr` — need C++14/17

```
CustomParameters.h:328:28: error: 'is_same_v' is not a member of 'std'
CustomParameters.h:328:28: error: expected primary-expression before ',' token
```

The example's `src/Makefile` hardcodes `-std=c++11`. The SDK's `CustomParameters.h` now uses `if constexpr` (C++17) and `std::is_same_v` (C++14). Bumping to `-std=c++17` clears this error but surfaces the next one.

### 5b. `std::span` — needs C++20

```
rp_acq_axi.h:149:99: error: 'span' is not a member of 'std'
rp_acq_axi.h:149:99: note: 'std::span' is only available from C++20 onwards
```

`rp_acq_axi.h` (part of the OS 3.00 SDK) now declares APIs using `std::vector<std::span<int16_t>>`. Bumped `-std=c++17` → `-std=c++20`.

**Fix applied in `app/src/Makefile`:**

```diff
-CXXFLAGS+=$(COMMON_FLAGS) -std=c++11 $(INCLUDE)
+CXXFLAGS+=$(COMMON_FLAGS) -std=c++20 $(INCLUDE)
```

### 5c. "template with C linkage"

```
In file included from /usr/include/c++/13/functional:59,
                 from /opt/redpitaya/include/apiApp/rpApp.h:15,
                 from main.cpp:13:
std_function.h:68:3: error: template with C linkage
main.cpp:12:1: note: 'extern "C"' linkage started here
```

`main.cpp` includes the SDK's app header like this:

```cpp
extern "C" {
    #include "rpApp.h"
}
```

`rpApp.h` is **not** a C header — it has no `__cplusplus` guard, and (in the OS 3.00 SDK) it `#include`s `<functional>` and `<vector>`. Templates cannot have C linkage, which is a hard compiler error under GCC 13. This pattern apparently worked under the older SDK/compiler pairing (likely because `rpApp.h` didn't pull in template-heavy STL headers at the time), but is invalid now.

**Fix applied in `app/src/main.cpp`:**

```diff
-extern "C" {
-    #include "rpApp.h"
-}
+#include "rpApp.h"
```

## 6. Out-of-memory during compilation

Even after the above fixes, the build died partway through with:

```
g++: fatal error: Killed signal terminated program cc1plus
compilation terminated.
```

`dmesg` confirmed an OOM kill:

```
Out of memory: Killed process NNNN (cc1plus) total-vm:112388kB, anon-rss:77184kB ...
```

`free -h` showed why: this STEMlab 125-10 has only **206 MiB of total RAM** and **no swap configured**. Compiling C++20 code against template-heavy STL/SDK headers (`<functional>`, `<span>`, JSON parsing headers) needs more resident memory than that during the `cc1plus` compile phase.

**Fix:** add temporary swap before building, remove it after:

```sh
fallocate -l 512M /root/swapfile   # or: dd if=/dev/zero of=/root/swapfile bs=1M count=512
chmod 600 /root/swapfile
mkswap /root/swapfile
swapon /root/swapfile

# build here

swapoff /root/swapfile
rm -f /root/swapfile
```

With swap available, the build completed cleanly and produced `controllerhf.so` (~130 KB).

## 7. Filesystem resize (informational — not needed here)

Red Pitaya's docs note that OS 2.07-43 and later auto-resize the root filesystem partition to the full SD card capacity on first boot (with an automatic second reboot to complete it), and that older OS versions need `/opt/redpitaya/sbin/resize.sh` run manually. On this board, `lsblk` after the OS 3.00 flash showed:

```
mmcblk0     7.5G
├─mmcblk0p1  973M  /opt/redpitaya, /boot
└─mmcblk0p2  6.6G  /
```

i.e. the root partition already spans essentially the full remaining card capacity — no manual resize was necessary.

## Summary of fixes applied

| Issue | File | Fix |
|---|---|---|
| C++11 too old for SDK | `app/src/Makefile` | `-std=c++11` → `-std=c++20` |
| Invalid `extern "C"` wrapper | `app/src/main.cpp` | Remove wrapper around `#include "rpApp.h"` |
| `/opt/redpitaya` read-only | (deploy step) | `mount -o remount,rw /opt/redpitaya` before deploying/building, remount `ro` after |
| `scp` SFTP failure | (deploy step) | Use `scp -O` (legacy protocol) |
| OOM during compile | (build step) | Temporary 512 MB swapfile during `make` |
