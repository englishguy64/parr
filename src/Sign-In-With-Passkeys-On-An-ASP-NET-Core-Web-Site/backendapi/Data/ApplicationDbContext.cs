using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace BackendApi.Data;

// With IdentitySchemaVersions.Version3 this context also creates the AspNetUserPasskeys table,
// which holds credentialId + PUBLIC key + signCount for each passkey.
public class ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
    : IdentityDbContext<ApplicationUser>(options)
{
}
