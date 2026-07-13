import pty, os, sys, select, time, re

def run(cmd, password, timeout=60):
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(cmd[0], cmd)
    else:
        output = b""
        sent_pw = False
        start = time.time()
        while time.time() - start < timeout:
            r, _, _ = select.select([fd], [], [], 1)
            if fd in r:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                if not sent_pw and re.search(rb"[Pp]assword:", output):
                    os.write(fd, (password + "\n").encode())
                    sent_pw = True
                    output = b""
            else:
                pid_done, status = os.waitpid(pid, os.WNOHANG)
                if pid_done != 0:
                    break
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        return output.decode(errors="replace")

if __name__ == "__main__":
    # usage: scp_rp.py <local_path> <remote_path> [-r] [-d (download: remote->local)]
    # Configure via env vars: RP_HOST (default rp-f0733a.local), RP_USER (default root),
    # RP_PASSWORD (default root).
    # Uses legacy SCP protocol (-O) since Red Pitaya's minimal sshd has no sftp-server,
    # which modern OpenSSH scp otherwise defaults to.
    host = os.environ.get("RP_HOST", "rp-f0733a.local")
    user = os.environ.get("RP_USER", "root")
    password = os.environ.get("RP_PASSWORD", "root")

    args = sys.argv[1:]
    recursive = "-r" in args
    download = "-d" in args
    args = [a for a in args if a not in ("-r", "-d")]
    local_path, remote_path = args[0], args[1]
    cmd = ["scp", "-O", "-o", "StrictHostKeyChecking=accept-new"]
    if recursive:
        cmd.append("-r")
    if download:
        cmd += [f"{user}@{host}:{remote_path}", local_path]
    else:
        cmd += [local_path, f"{user}@{host}:{remote_path}"]
    out = run(cmd, password)
    print(out)
