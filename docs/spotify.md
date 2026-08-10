# Spotify Remote (experimental)

Spotify Remote controls official Spotify clients and Connect devices. PlayQuick
does not download, decode, record, mix, or persist Spotify audio.

## Setup

1. Use a Spotify Premium account to create an application in the Spotify
   Developer Dashboard.
2. Register this exact Redirect URI (including the trailing slash):

   ```text
   https://beatbox4108.github.io/PlayQuick/spotify-callback/
   ```

   The page is static. It displays the authorization response for you to copy,
   then removes the query from the address bar. It does not exchange tokens,
   persist the response, load third-party resources, or make additional network
   requests. GitHub Pages necessarily receives the initial HTTPS request.
3. Paste the Client ID into PlayQuick Settings. Do not provide a Client Secret.
4. Enable library scopes only if Saved Tracks, Recently Played, and Top Tracks
   are wanted.
5. Run `uv run playquick spotify login` and approve the requested scopes.
6. Copy the complete callback URL shown by the page and paste it at PlayQuick's
   `Callback URL:` prompt. PlayQuick verifies the callback address and OAuth
   state before exchanging the short-lived code with its PKCE verifier.

PlayQuick opens the authorization URL in the default browser when possible. For
an SSH session, a headless machine, or when using a browser on another device,
print the URL without attempting to launch a browser:

```console
uv run playquick spotify login --no-browser
```

Open the printed URL in any browser, authorize PlayQuick, and paste the entire
result URL back into the waiting terminal. No inbound port or SSH port forwarding
is required.

Use `uv run playquick spotify logout` to remove the locally stored token. The
token is kept in the operating system credential store, never in `config.toml`.

Development Mode limits, endpoint availability, playlist visibility, Premium
requirements, and quotas are controlled by Spotify and can change independently
of PlayQuick. Public or editorial playlist contents may be unavailable. Spotify
search is intentionally paged in groups of ten.
