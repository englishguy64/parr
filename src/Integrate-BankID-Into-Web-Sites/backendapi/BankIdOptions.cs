/// <summary>
/// Every setting comes from an environment variable (App Service application settings in Azure) and none has a default.
/// If one is missing the backend does not start, and the error lists every missing variable.
///
///   BANKID_WEBSITE_URL                   the address of the web site in Azure. It is the only address a browser may call this API
///                                        from, and BankID returns a phone user to it after the BankID app
///   BANKID_TEST_URL                      BankID test endpoint
///   BANKID_TEST_KEYVAULT_URI             the Key Vault that holds the test certificate
///   BANKID_TEST_CERTIFICATE_NAME         Key Vault certificate for test
///   BANKID_TEST_ROOT_CA_PATH             BankID SSL root CA (PEM) for test
///   BANKID_TEST_CHECK_IP                 true or false
///   BANKID_PRODUCTION_URL, BANKID_PRODUCTION_KEYVAULT_URI, BANKID_PRODUCTION_CERTIFICATE_NAME,
///   BANKID_PRODUCTION_ROOT_CA_PATH, BANKID_PRODUCTION_CHECK_IP
///                                        the same five for production. The production vault is a separate Key Vault,
///                                        and the production certificate is uploaded to it by hand
/// </summary>
public sealed class AppSettings
{
    public required string WebSiteUrl { get; init; }

    /// <summary>The origin (scheme, host and port) of the web site, the only one a browser may call this API from.</summary>
    public string AllowedOrigin => new Uri(WebSiteUrl).GetLeftPart(UriPartial.Authority);

    /// <summary>BankID wants an https address to send a phone user back to, so there is none for a local http web site.</summary>
    public string? ReturnUrl => WebSiteUrl.StartsWith("https://", StringComparison.Ordinal) ? WebSiteUrl : null;

    public required BankIdEnvironment Test { get; init; }

    public required BankIdEnvironment Production { get; init; }

    public BankIdEnvironment For(string mode) => mode == BankIdModes.Production ? Production : Test;

    public static AppSettings FromEnvironment()
    {
        var problems = new List<string>();

        string Required(string name)
        {
            var value = Environment.GetEnvironmentVariable(name);
            if (string.IsNullOrWhiteSpace(value))
            {
                problems.Add($"{name} is not set");
                return "";
            }

            return value.Trim();
        }

        string HttpsUrl(string name)
        {
            var value = Required(name);
            if (value.Length > 0 && (!Uri.TryCreate(value, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps))
            {
                problems.Add($"{name} must be an https address");
                return "";
            }

            return value.Length > 0 ? new Uri(value).AbsoluteUri : "";
        }

        string WebSiteAddress(string name)
        {
            var value = Required(name);
            if (value.Length > 0 && (!Uri.TryCreate(value, UriKind.Absolute, out var uri)
                                     || (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp)))
            {
                problems.Add($"{name} must be an http or https address");
                return "";
            }

            return value.Length > 0 ? new Uri(value).AbsoluteUri : "";
        }

        bool Flag(string name)
        {
            var value = Required(name);
            if (value.Length > 0 && !bool.TryParse(value, out var flag))
            {
                problems.Add($"{name} must be true or false");
                return false;
            }

            return value.Length > 0 && bool.Parse(value);
        }

        BankIdEnvironment Environment_(string prefix) => new()
        {
            BaseUrl = HttpsUrl($"{prefix}_URL"),
            KeyVaultUri = HttpsUrl($"{prefix}_KEYVAULT_URI"),
            CertificateName = Required($"{prefix}_CERTIFICATE_NAME"),
            RootCaPath = Required($"{prefix}_ROOT_CA_PATH"),
            CheckIp = Flag($"{prefix}_CHECK_IP"),
        };

        var settings = new AppSettings
        {
            WebSiteUrl = WebSiteAddress("BANKID_WEBSITE_URL"),
            Test = Environment_("BANKID_TEST"),
            Production = Environment_("BANKID_PRODUCTION"),
        };

        if (problems.Count > 0)
        {
            throw new InvalidOperationException("Missing or invalid environment variables: " + string.Join("; ", problems));
        }

        return settings;
    }
}

public sealed class BankIdEnvironment
{
    /// <summary>Test: https://appapi2.test.bankid.com/rp/v6.0/ - Production: https://appapi2.bankid.com/rp/v6.0/</summary>
    public required string BaseUrl { get; init; }

    /// <summary>The Key Vault for this environment. Test and production use two separate vaults.</summary>
    public required string KeyVaultUri { get; init; }

    /// <summary>
    /// The name of the Key Vault certificate. Key Vault keeps the certificate with its private key as a secret of the same
    /// name, and the backend reads that secret. Test: the FPTestcert5 certificate. Production: ordered from your bank.
    /// </summary>
    public required string CertificateName { get; init; }

    /// <summary>The BankID SSL root CA (PEM) that issued the BankID server certificate. Different for test and production.</summary>
    public required string RootCaPath { get; init; }

    /// <summary>Require the ip in the /collect result to match the ip of the browser. Switch this on in production.</summary>
    public required bool CheckIp { get; init; }
}

public static class BankIdModes
{
    public const string Test = "test";
    public const string Production = "production";

    /// <summary>Anything but "production" is test, so a wrong value can never reach the real BankID.</summary>
    public static string Normalise(string? mode) =>
        string.Equals(mode, Production, StringComparison.OrdinalIgnoreCase) ? Production : Test;
}
