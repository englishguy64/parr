using System.Net.Http.Headers;
using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

/// <summary>A small client for the BankID Relying Party API v6.0 (/auth, /collect and /cancel).</summary>
public sealed class BankIdClient(HttpClient http)
{
    public record AuthResponse(string OrderRef, string AutoStartToken, string QrStartToken, string QrStartSecret);

    public record User(string PersonalNumber, string Name, string GivenName, string Surname);

    public record Device(string IpAddress);

    public record CompletionData(User User, Device Device);

    public record CollectResponse(string OrderRef, string Status, string? HintCode, CompletionData? CompletionData);

    public Task<AuthResponse> AuthAsync(string endUserIp, string? returnUrl)
    {
        var body = new Dictionary<string, object?> { ["endUserIp"] = endUserIp };
        if (returnUrl is not null) body["returnUrl"] = returnUrl;
        return PostAsync<AuthResponse>("auth", body);
    }

    public Task<CollectResponse> CollectAsync(string orderRef) =>
        PostAsync<CollectResponse>("collect", new Dictionary<string, object?> { ["orderRef"] = orderRef });

    public Task CancelAsync(string orderRef) =>
        PostAsync<JsonElement>("cancel", new Dictionary<string, object?> { ["orderRef"] = orderRef });

    /// <summary>
    /// The animated QR code. BankID wants a new code every second:
    /// bankid.{qrStartToken}.{seconds since the order}.{HMAC-SHA256(qrStartSecret, seconds) as hex}
    /// </summary>
    public static string QrData(string qrStartToken, string qrStartSecret, DateTimeOffset orderCreated)
    {
        var time = ((long)(DateTimeOffset.UtcNow - orderCreated).TotalSeconds).ToString();
        var hmac = HMACSHA256.HashData(Encoding.ASCII.GetBytes(qrStartSecret), Encoding.ASCII.GetBytes(time));
        return $"bankid.{qrStartToken}.{time}.{Convert.ToHexStringLower(hmac)}";
    }

    private async Task<T> PostAsync<T>(string method, object body)
    {
        // BankID answers 415 if the content type has a charset, so set the header by hand.
        using var content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
        using var response = await http.PostAsync(method, content);
        var text = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) throw new BankIdException(response.StatusCode, text);
        return JsonSerializer.Deserialize<T>(text, JsonSerializerOptions.Web)!;
    }

    /// <summary>
    /// The handler that talks to BankID. It presents the relying party certificate (the TLS client certificate)
    /// and trusts only the BankID SSL root CA for the environment.
    /// </summary>
    public static HttpMessageHandler CreateHandler(string rootCaPath, X509Certificate2 clientCertificate)
    {
        var handler = new SocketsHttpHandler { PooledConnectionLifetime = TimeSpan.FromMinutes(10) };
        handler.SslOptions.ClientCertificates = [clientCertificate];

        var pem = File.ReadAllText(rootCaPath);
        var root = PemEncoding.TryFind(pem, out var fields)
            ? X509CertificateLoader.LoadCertificate(Convert.FromBase64String(pem[fields.Base64Data]))
            : throw new InvalidOperationException($"{rootCaPath} is not a PEM certificate");

        handler.SslOptions.RemoteCertificateValidationCallback = (_, certificate, chain, errors) =>
        {
            if (certificate is null || (errors & SslPolicyErrors.RemoteCertificateNameMismatch) != 0) return false;

            using var custom = new X509Chain();
            custom.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
            custom.ChainPolicy.CustomTrustStore.Add(root);
            custom.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
            if (chain is not null)
            {
                foreach (var element in chain.ChainElements) custom.ChainPolicy.ExtraStore.Add(element.Certificate);
            }

            return custom.Build(new X509Certificate2(certificate));
        };

        return handler;
    }
}

public sealed class BankIdException(System.Net.HttpStatusCode status, string details)
    : Exception($"BankID returned {(int)status}: {details}")
{
    public System.Net.HttpStatusCode Status { get; } = status;
}
