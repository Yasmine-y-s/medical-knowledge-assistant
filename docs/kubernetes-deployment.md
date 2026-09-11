# Milestone 10, Part A — Kubernetes (local, via minikube)

## What this proves

Deployed the same containerized app from Milestone 8 to a local Kubernetes
cluster (minikube), replicating the Docker Compose setup as Kubernetes
manifests, and directly observed Kubernetes' self-healing behavior — a pod
was deliberately deleted and automatically replaced with no manual action.

## Concepts covered

- **Manifest**: a YAML file declaring a desired state; Kubernetes
  continuously works to keep reality matching it (declarative, not
  step-by-step imperative like `docker compose up`).
- **Pod**: the smallest running unit — roughly one container instance.
- **Deployment**: manages a desired number of pod replicas, restarting them
  automatically if they disappear.
- **Service**: a stable internal network address for reaching a set of
  pods, matched via labels/selectors rather than by name the way Compose
  services connect.
- **PersistentVolumeClaim (PVC)**: durable storage that survives pod
  restarts — the Kubernetes equivalent of a Docker named volume.
- **Secret**: Kubernetes-native credential storage, created directly via
  command (`kubectl create secret`) so real values never sit in a
  committed file.

## Steps actually taken, in order

1. Installed `minikube` and `kubectl`; started the local cluster with
   `minikube start`.
2. Wrote `k8s/postgres-pvc.yaml`, `k8s/postgres-deployment.yaml`,
   `k8s/postgres-service.yaml` — direct translation of the `postgres`
   service from `docker-compose.yml`.
3. Created a Secret directly via command (never written to a file):
   `kubectl create secret generic app-secrets --from-literal=SECRET_KEY=... --from-literal=OPENAI_API_KEY=...`
4. Wrote `k8s/app-deployment.yaml` (referencing the Secret via `envFrom`,
   and `DATABASE_URL` pointed at `postgres-service`, not `localhost`) and
   `k8s/app-service.yaml`.
5. Built the app image normally: `docker build -t medical-knowledge-assistant:latest .`
6. Loaded it into minikube's separate image storage:
   `minikube image load medical-knowledge-assistant:latest`
7. Applied everything at once: `kubectl apply -f k8s/`
8. Verified with `kubectl get pods` / `kubectl get deployments` until both
   showed `Running`, `1/1`.
9. Ran migrations inside the running pod:
   `kubectl exec -it <app-pod-name> -- alembic upgrade head`
10. Opened a tunnel to reach the app from a browser:
    `kubectl port-forward svc/app-service 8000:8000`, confirmed
    `localhost:8000/docs` loaded correctly.
11. **Proved self-healing**: found the app pod's name, ran
    `kubectl delete pod <name>`, and watched `kubectl get pods` show a
    brand-new pod already being created automatically, with zero manual
    intervention — full recovery within seconds.

## Worth remembering

- **minikube has its own separate image storage**, invisible to regular
  `docker build` — always `minikube image load <image>` after building,
  and verify with `minikube image ls | findstr <name>`.
- **`imagePullPolicy: Never` is required** on any locally-built image's
  Deployment manifest — otherwise Kubernetes tries to download it from
  Docker Hub and fails with `ImagePullBackOff`.
- **The Secret must exist BEFORE applying a Deployment that references
  it** — otherwise the pod fails to start.
- **`kubectl port-forward` blocks the terminal it runs in** — needs a
  second terminal window for any other `kubectl` commands while it's
  active.
- **Services connect by label/selector matching, not by name** — a real
  structural difference from Docker Compose's automatic service-name
  resolution.
