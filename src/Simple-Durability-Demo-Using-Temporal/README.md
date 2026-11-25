# Simple Durability Demo Using Temporal

A small C# order workflow that survives crashes. It matches the Manim diagram for this recipe: a Client starts a Workflow, a Worker runs the Workflow and its Activities, and the Temporal Service records every step in an Event History so a failed worker can pick up exactly where it left off.

One .NET 10 console app does both jobs. Run it as a **worker** or as a **client**.

## What is in this folder

| File | What it is |
|---|---|
| `Program.cs` | Connects to Temporal, then runs as `worker` or `client` |
| `OrderWorkflow.cs` | The Workflow: reserve stock, charge card, ship order |
| `OrderActivities.cs` | The three Activities that do the real work |
| `Order.cs` | The data passed into the Workflow |
| `Simple-Durability-Demo-Using-Temporal.csproj` | .NET 10 project with the `Temporalio` NuGet package |
| `Dockerfile` | Builds the app into a container image |
| `docker-compose.yml` | Runs a local Temporal server and a worker in containers |

## How the code maps to the diagram

| Diagram | Code |
|---|---|
| Client | `RunClientAsync` in `Program.cs`: starts a workflow and waits for the result |
| Task Queue | The `"orders"` string used by both the client and the worker |
| Worker | `RunWorkerAsync` in `Program.cs`: polls the task queue and runs your code |
| Workflow | `OrderWorkflow.cs` |
| Activities | `OrderActivities.cs` |
| Temporal Service | Not your code. Temporal runs it for you (Cloud), or you run it (local or self-hosted) |

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download)
- One Temporal Service to talk to. Pick one of the three options below.

## Where the Temporal Service runs

Your code is the same in every case. Only where the Temporal Service runs, and how you connect to it, changes.

| | Local dev server | Self-hosted | Temporal Cloud |
|---|---|---|---|
| **Who runs the Service** | You, on your laptop | You, in your own cluster | Temporal |
| **Typical use** | Learning and development | Production when you must run it yourself | Production without running the Service |
| **Start it** | `temporal server start-dev` | Docker Compose or Helm chart, then you maintain it | Create a namespace in the Cloud console |
| **Database** | Built in (SQLite, held in memory by default) | You run Cassandra, PostgreSQL or MySQL | Managed for you |
| **Address** | `localhost:7233` | Your own host name | `<namespace>.<account-id>.tmprl.cloud:7233` |
| **Namespace** | `default` | You create them | `<namespace>.<account-id>` |
| **Authentication** | None | Your choice (mTLS, authorizer plug-in) | API key or mutual TLS certificate |
| **Encryption in transit** | None | You set up TLS | Always TLS |
| **Web UI** | http://localhost:8233 | You deploy it | Cloud console |
| **Upgrades, backups, scaling** | Not needed | Your job | Temporal's job |
| **Cost** | Free | Infrastructure and people time | Pay per action and storage |
| **Your workers** | On your laptop | You host them | You host them. Temporal never runs your code |

Your Worker is always yours to host (a container in Azure, Kubernetes, a VM and so on), whichever Service you choose.

### Environment variables

`Program.cs` reads its connection settings from environment variables, so the same build runs against any option.

| Variable | Meaning | Default |
|---|---|---|
| `TEMPORAL_ADDRESS` | Host and port of the Temporal Frontend | `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Namespace to use | `default` |
| `TEMPORAL_API_KEY` | API key (Temporal Cloud, option 1). Turns TLS on | not set |
| `TEMPORAL_TLS_CERT` and `TEMPORAL_TLS_KEY` | Paths to a client certificate and key (mutual TLS) | not set |

Set the same variables for both the worker and the client.

## Run it: local dev server

1. Install the [Temporal CLI](https://docs.temporal.io/cli) and start a local server. It runs the Frontend, History, Matching and a database in one process, and a web UI.

   ```
   temporal server start-dev
   ```

   The server listens on `localhost:7233`. The web UI is at http://localhost:8233.

2. In this folder, start a worker in one terminal:

   ```
   dotnet run -- worker
   ```

3. Start a workflow from a second terminal:

   ```
   dotnet run -- client
   ```

   The client prints `Order ... shipped` and the worker prints the three activity lines.

No environment variables are needed. The defaults point at the local server.

## Run it: as a Docker container

The same app runs in a container, as a worker or as a client. The image is built from the `Dockerfile` (a multi-stage build on the .NET 10 SDK and runtime images). You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) or another Docker engine running.

### Pull the images

Docker pulls missing images automatically the first time you run or build, but you can pull them up front. This is useful on a slow connection or before going offline:

```
docker pull temporalio/temporal:latest
docker pull mcr.microsoft.com/dotnet/sdk:10.0
docker pull mcr.microsoft.com/dotnet/runtime:10.0
```

- `temporalio/temporal` is the Temporal server image that provides the local dev server. It is only needed when you run the Service in Docker yourself. You do not need it for Temporal Cloud.
- The two `mcr.microsoft.com/dotnet` images are the build and runtime base images used by the `Dockerfile`.

Your own `temporal-orders` image is not pulled from anywhere. You build it in the next step.

### Option A: everything in Docker with Compose

`docker-compose.yml` starts a local Temporal dev server and a worker. The worker connects to the server by its service name, `temporal:7233`.

```
docker compose up --build -d
```

Start a workflow with a one-off client container:

```
docker compose run --rm worker client
```

The client prints `Order ... shipped`, and `docker compose logs worker` shows the three activity lines. The web UI is at http://localhost:8233. Stop everything with `docker compose down`.

To see a failure recover, run `docker compose stop worker` after you see `charging`, start the client, then `docker compose start worker`. The new worker container replays the history and carries on.

### Option B: build and run the image yourself

1. Build the image from this folder:

   ```
   docker build -t temporal-orders .
   ```

2. Start a local Temporal server (skip this if you already have one running). If you did not pull the image above, this pulls it for you:

   ```
   docker run --rm -d --name temporal -p 7233:7233 -p 8233:8233 temporalio/temporal server start-dev --ip 0.0.0.0
   ```

3. Run a worker. Inside a container `localhost` means the container itself, so point at the host machine with `host.docker.internal` (Docker Desktop on Windows and macOS):

   ```
   docker run --rm -e TEMPORAL_ADDRESS=host.docker.internal:7233 temporal-orders worker
   ```

4. In a second terminal, run a client:

   ```
   docker run --rm -e TEMPORAL_ADDRESS=host.docker.internal:7233 temporal-orders client
   ```

On Linux add `--add-host=host.docker.internal:host-gateway` to the `docker run` commands, or put the containers on a shared Docker network and use the server container's name.

### Containers with a self-hosted Service or Temporal Cloud

Pass the same environment variables as before with `-e`, or keep them in an env file:

```
docker run --rm   -e TEMPORAL_ADDRESS=<address>   -e TEMPORAL_NAMESPACE=<namespace>.<account-id>   -e TEMPORAL_API_KEY=<your api key>   temporal-orders worker
```

For a client certificate, mount the files and point the variables at the mounted paths:

```
docker run --rm   -v C:\certs:/certs:ro   -e TEMPORAL_ADDRESS=<namespace>.<account-id>.tmprl.cloud:7233   -e TEMPORAL_NAMESPACE=<namespace>.<account-id>   -e TEMPORAL_TLS_CERT=/certs/client.pem   -e TEMPORAL_TLS_KEY=/certs/client.key   temporal-orders worker
```

Notes:

- Never bake keys or certificates into the image. Supply them at run time, and in production take them from a secret store such as Azure Key Vault or Kubernetes secrets.
- The worker container is the part you deploy to production (Azure Container Apps, Kubernetes, and so on). Run more than one copy to scale out and to survive a failure. Temporal Cloud does not run it for you.
- Keep the runtime image Debian based. The Temporal SDK needs glibc, so an Alpine image will not work.

## Run it: self-hosted Temporal Service

You deploy and operate the Service yourself, for example with the [Docker Compose](https://github.com/temporalio/docker-compose) files or the [Helm chart](https://github.com/temporalio/helm-charts) on Kubernetes, backed by your own PostgreSQL, MySQL or Cassandra.

```
$env:TEMPORAL_ADDRESS = "temporal.mycompany.internal:7233"
$env:TEMPORAL_NAMESPACE = "orders-prod"        # create it first, see below
dotnet run -- worker
```

(On macOS or Linux use `export TEMPORAL_ADDRESS=...`.)

What you own that you did not need locally:

- Create the namespace: `temporal operator namespace create orders-prod`
- Size, patch and upgrade the Frontend, History, Matching and Worker services
- Run, back up and monitor the database
- Set up TLS and authentication, and set the history retention period
- Deploy the web UI yourself

If your self-hosted Service uses mutual TLS, set `TEMPORAL_TLS_CERT` and `TEMPORAL_TLS_KEY`.

## Run it: Temporal Cloud

1. Sign up at [temporal.io](https://temporal.io/cloud) and create a **namespace**. The console shows its address and the full namespace name.
2. Authenticate with either:
   - an **API key** (create it in the console), or
   - a **client certificate**. Upload the CA certificate to the namespace and keep the client certificate and key safe.
3. Set the environment variables, then run the worker and client exactly as before.

   **API key**

   ```
   $env:TEMPORAL_ADDRESS = "<address shown in the console>"
   $env:TEMPORAL_NAMESPACE = "<namespace>.<account-id>"
   $env:TEMPORAL_API_KEY = "<your api key>"
   dotnet run -- worker
   ```

   **Client certificate (mutual TLS)**

   ```
   $env:TEMPORAL_ADDRESS = "<namespace>.<account-id>.tmprl.cloud:7233"
   $env:TEMPORAL_NAMESPACE = "<namespace>.<account-id>"
   $env:TEMPORAL_TLS_CERT = "C:\certs\client.pem"
   $env:TEMPORAL_TLS_KEY = "C:\certs\client.key"
   dotnet run -- worker
   ```

4. Open the Cloud console to see the workflow and its Event History.

Things to know:

- Keep keys and certificates out of source control. In production read them from a secret store such as Azure Key Vault.
- Workflow inputs and results are stored in the Event History on Temporal's side. If they are sensitive, add a payload codec so they are encrypted before they leave your worker.
- Your worker still runs on your infrastructure. Temporal Cloud only replaces the Temporal Service box in the diagram.
- Take the exact address and the API key endpoint format from the Cloud console. They depend on your region and cloud provider.

## See a failure recover

1. Start the Service and a worker as above, then start the client.
2. Stop the worker (Ctrl+C) after you see `charging`.
3. Start the worker again. A new worker replays the Event History, skips Reserve Stock and Charge Card, and carries on with Ship Order. Nothing is charged twice.
4. Open the web UI (local) or the Cloud console to inspect the history.

The activities here only print to the console. In a real system they must be safe to run more than once, because Temporal retries an activity that fails or times out.

## Rules for workflow code

The workflow is replayed from its history, so it must give the same answer every time. Inside `OrderWorkflow` do not use `DateTime.Now`, `Guid.NewGuid()`, random numbers or direct network calls. Put those in activities. Use the `Workflow` helper methods for time and delays.

## Documentation

- [Temporal .NET developer guide](https://docs.temporal.io/develop/dotnet)
- [Temporal Cloud](https://docs.temporal.io/cloud)
- [Self-hosted Temporal Service](https://docs.temporal.io/self-hosted-guide)
