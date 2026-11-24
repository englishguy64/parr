using System.Runtime.CompilerServices;
using Microsoft.Extensions.AI;

// Stands in for Foundry when FOUNDRY_PROJECT_ENDPOINT is not set, so the website and the AG-UI flow can be tried on a PC
// without Azure. It streams a canned answer word by word.
internal sealed class StubChatClient(string name) : IChatClient
{
    public async IAsyncEnumerable<ChatResponseUpdate> GetStreamingResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var last = messages.LastOrDefault(m => m.Role == ChatRole.User)?.Text ?? "";
        var text = $"(Stub '{name}': FOUNDRY_PROJECT_ENDPOINT is not set, so no Foundry agent was called.) You said: {last}";
        var messageId = $"msg_{Guid.NewGuid():N}";   // one id for the whole answer, as Foundry does, so it is one message
        foreach (var word in text.Split(' '))
        {
            await Task.Delay(60, cancellationToken);
            yield return new ChatResponseUpdate(ChatRole.Assistant, word + " ") { MessageId = messageId };
        }
    }

    public async Task<ChatResponse> GetResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null, CancellationToken cancellationToken = default)
    {
        var updates = new List<ChatResponseUpdate>();
        await foreach (var u in GetStreamingResponseAsync(messages, options, cancellationToken)) updates.Add(u);
        return updates.ToChatResponse();
    }

    public object? GetService(Type serviceType, object? serviceKey = null) => null;
    public void Dispose() { }
}
