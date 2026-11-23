using Microsoft.AspNetCore.Identity;

namespace BackendApi.Data;

// No password column is ever filled in: this demo users sign in with passkeys only.
public class ApplicationUser : IdentityUser
{
}
