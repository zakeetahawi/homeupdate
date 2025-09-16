Postgres systemd protection and monitoring (homeupdate)
=====================================================

What this adds
--------------
- A script to create a systemd drop-in override for the `postgresql.service` to set `Restart=on-failure` and `RestartSec=5`.
- A small healthcheck script that appends status lines to `logs/postgres-monitor.log`.
- Example `systemd` units (`postgres-healthcheck.service` and `postgres-healthcheck.timer`) you can install to run the healthcheck every minute.

Files added
-----------
- `scripts/setup-postgres-systemd.sh`  - create the drop-in override (run as root)
- `scripts/postgres-healthcheck.sh`   - healthcheck script
- `systemd/postgres-healthcheck.service` - example unit that runs the healthcheck
- `systemd/postgres-healthcheck.timer`   - example timer to run the check periodically

How to apply the systemd override (recommended)
------------------------------------------------
1. Run the setup script as root to create the override and restart Postgres:

   sudo bash scripts/setup-postgres-systemd.sh

2. Confirm the override exists:

   sudo systemctl show --property=FragmentPath postgresql

3. Verify Postgres is running and will restart on failure:

   sudo systemctl daemon-reload
   sudo systemctl restart postgresql
   sudo systemctl status postgresql

Optional: enable periodic healthchecks via systemd timer
------------------------------------------------------
If you want the repository-provided timer to run the healthcheck every minute and create journal entries:

1. Copy the example units to `/etc/systemd/system`:

   sudo cp systemd/postgres-healthcheck.service /etc/systemd/system/
   sudo cp systemd/postgres-healthcheck.timer /etc/systemd/system/

2. Reload systemd and enable/start the timer:

   sudo systemctl daemon-reload
   sudo systemctl enable --now postgres-healthcheck.timer

3. See recent runs with:

   journalctl -u postgres-healthcheck.service -f

Notes and security
------------------
- The healthcheck script writes to `logs/postgres-monitor.log` in the repository. Ensure appropriate file permissions for multi-user systems.
- The example service runs the script as `root` for simplicity; for a hardened setup, create a dedicated user with limited privileges and adjust `User=`/`Group=` in the service file.
- This change does not modify any database or application code; it only affects systemd service behavior and adds monitoring helpers.
