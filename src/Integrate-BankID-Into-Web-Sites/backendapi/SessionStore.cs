using System.Collections.Concurrent;
using System.Security.Cryptography;

/// <summary>
/// Signed in users, held in memory. The proof of sign in is a random 256 bit token that the browser sends as a Bearer token.
/// A restart signs everyone out. Use a shared cache such as Redis if you run more than one instance.
/// </summary>
public sealed class SessionStore
{
    public record SignedInUser(string PersonalNumber, string Name, string GivenName, string Surname);

    private record Session(SignedInUser User, DateTimeOffset Expires);

    private static readonly TimeSpan Lifetime = TimeSpan.FromHours(1);
    private readonly ConcurrentDictionary<string, Session> sessions = new();

    public string Create(SignedInUser user)
    {
        Purge();
        var token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
        sessions[token] = new Session(user, DateTimeOffset.UtcNow + Lifetime);
        return token;
    }

    public SignedInUser? Find(string? token)
    {
        if (token is null || !sessions.TryGetValue(token, out var session)) return null;
        if (session.Expires > DateTimeOffset.UtcNow) return session.User;
        sessions.TryRemove(token, out _);
        return null;
    }

    public void Remove(string? token)
    {
        if (token is not null) sessions.TryRemove(token, out _);
    }

    private void Purge()
    {
        foreach (var (token, session) in sessions)
        {
            if (session.Expires <= DateTimeOffset.UtcNow) sessions.TryRemove(token, out _);
        }
    }
}
