FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY policy-check.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app .
# Hosted Agents listen on 8088 and answer POST /responses.
ENV ASPNETCORE_URLS=http://+:8088
EXPOSE 8088
ENTRYPOINT ["dotnet", "policy-check.dll"]
