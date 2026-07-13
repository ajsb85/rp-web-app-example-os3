import pty, os, sys, select, time, re

def run(cmd, password, timeout=180):
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
                # no data momentarily; check if child exited
                pid_done, status = os.waitpid(pid, os.WNOHANG)
                if pid_done != 0:
                    break
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        return output.decode(errors="replace")

if __name__ == "__main__":
    # Non-interactive SSH for environments without ssh-askpass/sshpass/expect.
    # Configure via env vars: RP_HOST (default rp-f0733a.local), RP_USER (default root),
    # RP_PASSWORD (default root).
    host = os.environ.get("RP_HOST", "rp-f0733a.local")
    user = os.environ.get("RP_USER", "root")
    password = os.environ.get("RP_PASSWORD", "root")
    remote_cmd = sys.argv[1] if len(sys.argv) > 1 else "echo connected; hostname; uname -a"
    cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=5",
           f"{user}@{host}", remote_cmd]
    out = run(cmd, password)
    print(out)
