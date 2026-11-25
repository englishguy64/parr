using Temporalio.Activities;

namespace TemporalApp;

// Activities do the real work: call APIs, databases, payment providers and so on.
// If an activity throws, Temporal retries it. Make them safe to run more than once.
public class OrderActivities
{
    [Activity]
    public Task ReserveStockAsync(Order order)
    {
        Console.WriteLine($"  Activity: reserving stock for order {order.Id}");
        return Task.CompletedTask;
    }

    [Activity]
    public Task ChargeCardAsync(Order order)
    {
        Console.WriteLine($"  Activity: charging {order.Amount:C} for order {order.Id}");
        return Task.CompletedTask;
    }

    [Activity]
    public Task ShipOrderAsync(Order order)
    {
        Console.WriteLine($"  Activity: shipping order {order.Id}");
        return Task.CompletedTask;
    }
}
