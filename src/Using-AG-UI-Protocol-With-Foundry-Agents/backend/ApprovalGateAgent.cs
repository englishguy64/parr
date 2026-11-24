using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using AGUI.Abstractions;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;

// Human in the loop for an existing Foundry agent.
//
// A Foundry Prompt Agent owns its own tools, so a client-side tool that needs approval can't be added to it at request time.
// This agent wraps the Prompt Agent and puts the approval step in front of the action instead:
//
//   run 1  the wrapped agent drafts a customer reply (streamed as normal text), then this agent asks for approval to call
//          the tool "send_customer_reply". AG-UI ends the run with an interrupt and the page shows Approve / Reject.
//   run 2  the page sends the decision (the resume payload {"approved": true|false}). Approved: the reply is "sent" (simulated here). Rejected: nothing is sent.
//
// AG-UI turns a ToolApprovalRequestContent into the interrupt, and the resume entry back into an InterruptResponseContent.
// The server keeps no state between the two runs: the decision is all the second run needs.
internal sealed class ApprovalGateAgent(AIAgent inner) : DelegatingAIAgent(inner)
{
    private const string ToolName = "send_customer_reply";

    protected override async IAsyncEnumerable<AgentResponseUpdate> RunCoreStreamingAsync(
        IEnumerable<ChatMessage> messages, AgentSession? session, AgentRunOptions? options,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var history = messages.ToList();

        // Run 2: the person has decided. AG-UI delivers the answer to the interrupt as InterruptResponseContent, with the
        // payload the page sent ({"approved": true|false}). A cancelled interrupt has no payload and counts as a rejection.
        var response = history.SelectMany(m => m.Contents).OfType<InterruptResponseContent>().LastOrDefault();
        if (response is not null)
        {
            yield return Text(IsApproved(response)
                ? "Approved. The reply was sent to the customer (simulated: nothing leaves this demo)."
                : "Rejected. Nothing was sent to the customer.");
            yield break;
        }

        // Run 1: let the Foundry agent draft the reply, streaming it to the page as it arrives.
        var draft = new StringBuilder();
        await foreach (var update in InnerAgent.RunStreamingAsync(history, session, options, cancellationToken))
        {
            draft.Append(update.Text);
            yield return update;
        }

        // Then ask a person before the "send" action happens.
        var call = new FunctionCallContent(
            callId: $"call_{Guid.NewGuid():N}",
            name: ToolName,
            arguments: new Dictionary<string, object?> { ["reply"] = draft.ToString() });

        yield return new AgentResponseUpdate(ChatRole.Assistant,
            [new ToolApprovalRequestContent($"approval_{Guid.NewGuid():N}", call)]);
    }

    private static bool IsApproved(InterruptResponseContent response)
    {
        if (response.Payload is null) return false;
        var json = JsonSerializer.SerializeToElement(response.Payload);
        return json.ValueKind == JsonValueKind.Object
            && json.TryGetProperty("approved", out var approved)
            && approved.ValueKind == JsonValueKind.True;
    }

    private static AgentResponseUpdate Text(string text) =>
        new(ChatRole.Assistant, text) { MessageId = $"msg_{Guid.NewGuid():N}" };
}
