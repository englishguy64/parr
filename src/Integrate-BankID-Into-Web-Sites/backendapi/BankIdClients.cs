using System.Collections.Concurrent;
using System.Security.Cryptography.X509Certificates;
using Azure.Identity;
using Azure.Security.KeyVault.Secrets;
using Microsoft.Extensions.Options;

/// <summary>
/// One BankIdClient for test and one for production. Each gets its relying party certificate from Azure Key Vault the first
/// time it is used, so the test mode works even before you have a production certificate.
/// </summary>
public sealed class BankIdClients(IOptions<BankIdOptions> options)
{
    private readonly ConcurrentDictionary<string, Lazy<Task<BankIdClient>>> clients = new();

    public async Task<BankIdClient> GetAsync(string mode)
    {
        var lazy = clients.GetOrAdd(mode, m => new Lazy<Task<BankIdClient>>(() => CreateAsync(m)));
        try
        {
            return await lazy.Value;
        }
        catch
        {
            clients.TryRemove(mode, out _); // try again next time, for example after the certificate was uploaded
            throw;
        }
    }

    public BankIdEnvironment Settings(string mode) => options.Value.For(mode);

    private async Task<BankIdClient> CreateAsync(string mode)
    {
        var settings = options.Value.For(mode);
        var certificate = await LoadCertificateAsync(options.Value.KeyVaultUri, settings.CertificateSecretName);
        var http = new HttpClient(BankIdClient.CreateHandler(settings, certificate))
        {
            BaseAddress = new Uri(settings.BaseUrl),
        };
        return new BankIdClient(http);
    }

    /// <summary>
    /// Reads the certificate from Azure Key Vault. The backend signs in with its own identity (DefaultAzureCredential:
    /// managed identity in Azure, your az login on your PC) and needs the Key Vault Secrets User role.
    /// </summary>
    private static async Task<X509Certificate2> LoadCertificateAsync(string keyVaultUri, string secretName)
    {
        if (string.IsNullOrEmpty(keyVaultUri))
        {
            throw new InvalidOperationException("BankId:KeyVaultUri is not set. See the README.");
        }

        var secrets = new SecretClient(new Uri(keyVaultUri), new DefaultAzureCredential());
        KeyVaultSecret secret = await secrets.GetSecretAsync(secretName);
        return X509CertificateLoader.LoadPkcs12(Convert.FromBase64String(secret.Value), null);
    }
}
