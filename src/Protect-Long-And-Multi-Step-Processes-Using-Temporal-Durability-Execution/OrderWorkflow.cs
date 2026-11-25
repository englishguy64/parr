using Temporalio.Workflows;

namespace TemporalApp;

// The workflow orchestrates the steps. It must be deterministic: no DateTime.Now, Guid.NewGuid(),
// random numbers or direct network calls. Put those in activities.
[Workflow]
public class OrderWorkflow
{
    [WorkflowRun]
    public async Task<string> RunAsync(Order order)
    {
        // Timeouts and retries are set on the activity call, not inside the activity.
        var options = new ActivityOptions { StartToCloseTimeout = TimeSpan.FromSeconds(30) };

        // Each call below is recorded in the Event History when it completes.
        // After a crash the workflow replays that history and skips the finished steps.
        await Workflow.ExecuteActivityAsync((OrderActivities a) => a.ReserveStockAsync(order), options);
        await Workflow.ExecuteActivityAsync((OrderActivities a) => a.ChargeCardAsync(order), options);
        await Workflow.ExecuteActivityAsync((OrderActivities a) => a.ShipOrderAsync(order), options);

        return $"Order {order.Id} shipped";
    }
}
