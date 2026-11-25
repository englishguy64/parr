using Temporalio.Client;
using Temporalio.Worker;
using TemporalApp;

// Usage:
//   dotnet run -- worker     runs a Worker that polls the Task Queue and executes workflow and activity code
//   dotnet run -- client     starts one OrderWorkflow and waits for its result
//
// Connection settings come from environment variables. With none set it uses a local dev server
// (temporal server start-dev). See README.md for Temporal Cloud.

const string TaskQueue = "orders";

var client = await ConnectAsync();

switch (args.FirstOrDefault()?.ToLowerInvariant())
{
    case "worker":
        await RunWorkerAsync(client);
        break;
    case "client":
        await RunClientAsync(client);
        break;
    default:
        Console.WriteLine("Usage: dotnet run -- worker | client");
        break;
}

static async Task<ITemporalClient> ConnectAsync()
{
    var address = Environment.GetEnvironmentVariable("TEMPORAL_ADDRESS") ?? "localhost:7233";
    var options = new TemporalClientConnectOptions(address)
    {
        Namespace = Environment.GetEnvironmentVariable("TEMPORAL_NAMESPACE") ?? "default",
    };

    // Temporal Cloud, option 1: API key
    var apiKey = Environment.GetEnvironmentVariable("TEMPORAL_API_KEY");
    if (!string.IsNullOrEmpty(apiKey))
    {
        options.ApiKey = apiKey;
        options.Tls = new TlsOptions();
    }

    // Temporal Cloud, option 2: mutual TLS client certificate
    var certPath = Environment.GetEnvironmentVariable("TEMPORAL_TLS_CERT");
    var keyPath = Environment.GetEnvironmentVariable("TEMPORAL_TLS_KEY");
    if (!string.IsNullOrEmpty(certPath) && !string.IsNullOrEmpty(keyPath))
    {
        options.Tls = new TlsOptions
        {
            ClientCert = await File.ReadAllBytesAsync(certPath),
            ClientPrivateKey = await File.ReadAllBytesAsync(keyPath),
        };
    }

    return await TemporalClient.ConnectAsync(options);
}

static async Task RunWorkerAsync(ITemporalClient client)
{
    using var worker = new TemporalWorker(
        client,
        new TemporalWorkerOptions(TaskQueue)
            .AddAllActivities(new OrderActivities())
            .AddWorkflow<OrderWorkflow>());

    using var cts = new CancellationTokenSource();
    Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

    Console.WriteLine($"Worker polling task queue '{TaskQueue}'. Press Ctrl+C to stop.");
    try
    {
        await worker.ExecuteAsync(cts.Token);
    }
    catch (OperationCanceledException)
    {
        Console.WriteLine("Worker stopped.");
    }
}

static async Task RunClientAsync(ITemporalClient client)
{
    var order = new Order(Id: DateTime.UtcNow.ToString("yyyyMMddHHmmss"), Amount: 49.99m);

    // The workflow id identifies this run. Starting the same id twice is rejected by default.
    var handle = await client.StartWorkflowAsync(
        (OrderWorkflow wf) => wf.RunAsync(order),
        new WorkflowOptions(id: $"order-{order.Id}", taskQueue: TaskQueue));

    Console.WriteLine($"Started workflow {handle.Id}. Waiting for the result...");
    Console.WriteLine(await handle.GetResultAsync());
}
