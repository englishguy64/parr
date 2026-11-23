# Parr Receipes

A static web site of short, illustrated "receipes" (technical how-tos) that act as an addendum to my [LinkedIn profile](https://www.linkedin.com/in/john-parr-7567521a7/). Each receipe is a short description with an MP4 video walkthrough and, where relevant, links to Microsoft documentation and source code.

## Topics

Receipes are grouped into tabs:

- **API Management** - Azure APIM policies, subscriptions, managed identities, and authorising Angular SPAs and Claude.
- **Foundry** - Microsoft Foundry agents and toolboxes.
- **Other** - MCP connectors and passkey sign-in with ASP.NET Core.

## AI assistance

Claude iteration cycles were used to generate this web site, the GitHub source code and the MP4 videos. Verification effort and lack of trust expand exponentially with solution complexity. Over time verification discipline will give way to resource constraints and delivery pressure.

## Disclaimer

Azure SKUs are for cost saving, not production. SDKs used are in preview and will change. Receipes are for guidance only and will become out of date. Check the latest documentation for innovations and breaking changes.

## Repository layout

| Path | Purpose |
| --- | --- |
| `index.html`, `styles.css`, `scripts.js`, `icons.js` | The static site (no build step). `scripts.js` builds the topic tabs and video flyout. |
| `manim/` | [Manim](https://www.manim.community/) scripts that render the MP4 diagram videos. |
| `src/` | Source code for receipes that have a working sample. |

## Running locally

Open `index.html` in a browser, or serve the folder with any static file server.

To render a video, from `manim/` run for example:

```
manim -pqh Use-Claude-MCP-Connectors-With-APIs.py
```

## License

See [LICENSE](LICENSE).
