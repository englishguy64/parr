using System.Runtime.CompilerServices;
using Microsoft.Extensions.AI;

// Stands in for the chat model when FOUNDRY_PROJECT_ENDPOINT is not set, so the AG-UI endpoint can be tried on a PC without
// Azure. It streams a canned answer word by word.
internal sealed class StubChatClient : IChatClient
{
    public async IAsyncEnumerable<ChatResponseUpdate> GetStreamingResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var last = messages.LastOrDefault(m => m.Role == ChatRole.User)?.Text ?? "";
        var text = $"(Stub a2ui-stream agent: FOUNDRY_PROJECT_ENDPOINT is not set, so no chat model was called.) You asked: {last}";
        var messageId = $"msg_{Guid.NewGuid():N}";
        foreach (var word in text.Split(' '))
        {
            await Task.Delay(80, cancellationToken);
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
