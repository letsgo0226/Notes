# HSI Music Renderer Bridge

Public bridge endpoint:

`https://hsi-music-render-bridge-production.up.railway.app/render`

Health endpoint:

`https://hsi-music-render-bridge-production.up.railway.app/health`

Protocol: `HSI-MUSIC-RENDER-BRIDGE/1.0`

The bridge accepts `HSI-MUSIC-2K/1` keyword requests, generates original lyrics first, then renders a sung song. It is intentionally fail-closed until both Railway variables below are present:

- `FAL_KEY`
- `HSI_BRIDGE_TOKEN`

Non-secret default: `HSI_MUREKA_MODEL=mureka-9.5`.

The provider key and bridge token must be entered directly in Railway Variables. Do not commit them to Git.

After those variables are configured, iSH uses:

```sh
export HSI_RENDER_URL="https://hsi-music-render-bridge-production.up.railway.app/render"
export HSI_RENDER_TOKEN="YOUR_BRIDGE_TOKEN"
sh ~/Notes/hsi_music_2kb.sh
```

Then enter keywords at the `keywords>` prompt.

A successful run creates its own folder under `~/Music/HSI/` and writes `hsi2k.keywords`, `hsi2k.txt`, `hsi2k.mp3`, `hsi2k.e257`, and `hsi2k.cert`.

The 2 KB kernel does not contain or expose provider credentials.
