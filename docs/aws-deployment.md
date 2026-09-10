# Milestone 9 — AWS Deployment Notes

## What this proves

Successfully deployed the fully containerized app (from Milestone 8) to a real
AWS EC2 instance, confirmed reachable from the public internet via Swagger UI
at `/docs`. Instance was terminated after confirming success — this was a
one-time deployment proof, not a permanently running production instance.

## Concepts covered

- **IAM**: created a non-root admin user; never used root for daily work.
- **EC2**: a rented virtual computer (t3.micro, Ubuntu, 1 vCPU/1GB RAM).
- **Security groups**: AWS's firewall — only opened port 22 (SSH) and 8000 (app).
- **Key pairs**: `.pem` file-based SSH auth, no passwords.
- **EBS**: the instance's attached disk — survives Stop, destroyed on Terminate.
- **Secrets**: `.env` created manually on the server via SSH (pragmatic choice
  for this project; AWS Secrets Manager is the real production approach).

## Steps actually taken, in order

1. Created AWS account.
2. Created an IAM user with AdministratorAccess; stopped using root.
3. Launched a t3.micro Ubuntu instance; created and downloaded a `.pem` key pair.
4. Configured security group: SSH (22) restricted to my current public IP (/32) for key-based SSH access; port 8000 open to everyone for external access to the FastAPI application.
5. Fixed Windows `.pem` file permissions (Properties > Security >
   Advanced > Disable inheritance > remove all but my own account + SYSTEM)
   to resolve "UNPROTECTED PRIVATE KEY FILE" error.
6. Connected via `ssh -i "key.pem" ubuntu@<public-ip>`.
7. Installed Docker + Compose plugin via Docker's official apt repo.
8. `git clone`d the repo directly onto the server.
9. Manually created `.env` on the server (`nano .env`) with real
   SECRET_KEY / OPENAI_API_KEY.
10. `docker compose up -d --build`, then `docker exec ... alembic upgrade head`.
11. Confirmed `http://<public-ip>:8000/docs` loaded correctly from my own
    browser — real, independent proof of a working deployment.
12. Took screenshots (see `docs/screenshots/`).
13. Terminated the instance — the goal was proving deployability, not
    maintaining a permanent server.

## Worth remembering

- **Stopping ≠ terminating**: stopping preserves the EBS volume (and your
  data); terminating deletes it by default. Stop between sessions, never
  leave running idle.
- **The public IP changes every time you stop/start the instance** (if no
  Elastic IP was set up) — always re-check it before reconnecting.
- **Deploying code changes** = git pull on the server, then
  `docker compose down && docker compose up -d --build`.
