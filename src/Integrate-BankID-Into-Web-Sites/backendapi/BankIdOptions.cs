/// <summary>
/// The test and production environments of BankID side by side. The same C# code serves both.
/// The web site picks the mode for each sign in, and the backend picks that environment's settings and certificate.
/// </summary>
public sealed class BankIdOptions
{
    /// <summary>The Azure Key Vault that holds both relying party certificates, for example https://myvault.vault.azure.net/</summary>
    public string KeyVaultUri { get; set; } = "";

    public BankIdEnvironment Test { get; set; } = new();

    public BankIdEnvironment Production { get; set; } = new();

    public BankIdEnvironment For(string mode) => mode == BankIdModes.Production ? Production : Test;
}

public sealed class BankIdEnvironment
{
    /// <summary>Test: https://appapi2.test.bankid.com/rp/v6.0/ - Production: https://appapi2.bankid.com/rp/v6.0/</summary>
    public string BaseUrl { get; set; } = "";

    /// <summary>
    /// The name of the Key Vault certificate. Key Vault keeps the certificate with its private key as a secret of the same
    /// name, and the backend reads that secret. Test: the FPTestcert5 certificate. Production: ordered from your bank.
    /// </summary>
    public string CertificateSecretName { get; set; } = "";

    /// <summary>The BankID SSL root CA (PEM) that issued the BankID server certificate. Different for test and production.</summary>
    public string RootCaPath { get; set; } = "";

    /// <summary>Require the ip in the /collect result to match the ip of the browser. Switch this on in production.</summary>
    public bool CheckIp { get; set; } = true;
}

public static class BankIdModes
{
    public const string Test = "test";
    public const string Production = "production";

    /// <summary>Anything but "production" is test, so a wrong value can never reach the real BankID.</summary>
    public static string Normalise(string? mode) =>
        string.Equals(mode, Production, StringComparison.OrdinalIgnoreCase) ? Production : Test;
}
