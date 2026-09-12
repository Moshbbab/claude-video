# /watch

Give an agent video evidence: a URL or local file becomes timestamped frames and a transcript. Works with Claude Code and other [Agent Skills](https://agentskills.io) hosts, including Codex, Cursor, and Copilot. Native captions come first; optional local WhisperX or Groq/OpenAI transcription handles videos without captions.

## Install and get a first result

**Claude Code:** type these in Claude Code, then reload the host and check skill autocomplete. Depending on the host version, the plugin skill may appear as `/watch:watch`.

```text
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

**Other Agent Skills hosts:** run this in your terminal. Node/npm is needed for this installer, not for watch's Python runtime. Follow the CLI's reported destination, then restart the agent.

```bash
npx skills add bradautomates/claude-video -g --skill watch
# Optional: target a host explicitly with -a codex
```

**Hosted claude.ai:** download the `watch.skill` asset from [Releases](https://github.com/bradautomates/claude-video/releases/latest) and upload it through the Skills settings. GitHub's source ZIP is not the `.skill` asset. Tool execution and network egress are separate: a hosted environment may run binaries but block video/CDN/API/model hosts. Check your account's [execution and network settings](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude).

Install media dependencies in the same environment as the agent: **Python 3.10+, FFmpeg/ffprobe, and current yt-dlp**. YouTube also needs a supported JavaScript runtime/EJS setup. The first-run skill can install missing media tools with Homebrew on macOS; elsewhere it supplies commands.

| Platform | Terminal commands |
|---|---|
| macOS | Install [Homebrew](https://brew.sh), then `brew install python ffmpeg yt-dlp`. Current yt-dlp formula includes Deno/EJS/curl-cffi. |
| Ubuntu/Debian | `sudo apt install python3 ffmpeg pipx`, then `pipx install "yt-dlp[default,curl-cffi]"` and `pipx ensurepath`. Install [Deno](https://docs.deno.com/runtime/getting_started/installation/) for YouTube. |
| Windows | Install Python 3.10+, then `winget install --id Gyan.FFmpeg --exact`, `winget install --id yt-dlp.yt-dlp --exact`, and `winget install --id DenoLand.Deno --exact`. |

Reopen the terminal/agent after PATH changes. Verify `ffmpeg -version`, `ffprobe -version`, and `yt-dlp --version`. On Windows, use a working `python` or `py -3`; inspect `--version` rather than assuming all `python3` commands are Store aliases. The tested yt-dlp baseline is **2026.08.19**; watch runs the executable on PATH rather than pinning a Python dependency.

For a first success, give the agent a **short local video**, with no key required:

```text
/watch /absolute/path/to/video.mp4 --no-whisper
```

If your host does not expose slash commands, ask it to use the watch skill on that file with speech fallback disabled. The first-run wizard lets you choose `balanced` detail and `none` for the saved transcription backend. The agent locates the bundled scripts itself, reads the extracted images, and returns a timestamped summary. This confirms local extraction independently of network access.

Next, try a public captioned video with `--detail transcript`. Caption-only success reports the selected language and source without downloading media. Not every public URL has captions or permits anonymous access.

## Choose a transcription fallback

The first-run wizard asks once for your detail preference and for a fallback backend. Captions remain first under every choice.

| Backend | Requirements and behavior |
|---|---|
| `whisperx` (recommended) | Local transcription, no API key. The skill manages a separate Python 3.12 environment and warms its model caches. |
| `groq` | Cloud `whisper-large-v3`; needs `GROQ_API_KEY` from [Groq](https://console.groq.com/keys). |
| `openai` | Cloud `whisper-1`; needs `OPENAI_API_KEY` from [OpenAI](https://platform.openai.com/api-keys). |
| `none` | Captions only. Local files and captionless URLs can still provide visual evidence. |

Existing 0.2.0 users retain `auto`: Groq key first, then OpenAI. No automatic migration to local inference. Explicit `--whisper groq|openai|whisperx` overrides this run's fallback, while `--no-whisper` disables all fallbacks and still permits native captions. Those two flags conflict.

Settings live in `~/.config/watch/.env`. Enter keys privately there or in the process environment; do not commit them or paste them into public issues. Cloud-key lookup is provider preference first, then environment → user file → cwd `.env` for each provider. Explicit providers never borrow another provider's key. Config files support UTF-8, UTF-8 BOM, and BOM-marked UTF-16; quotes, comments, and literal Windows paths work without shell expansion. Last assignment wins.

### Managed WhisperX

Have the agent run the bundled `setup.py --install-whisperx` (or `--backend whisperx --detail balanced`). It provisions uv if needed, installs Python 3.12 and **WhisperX 3.8.6**, and transcribes two seconds of silence to warm the Whisper and Silero caches. No sudo is used by the installer. The base watch process stays standard-library-only and can use newer Python independently.

| Requirement | Guidance |
|---|---|
| Free disk | At least **3 GB** for the environment, small model, installer cache, and managed Python |
| RAM | At least **8 GB**; reference small-model peak process memory was about 2.4 GB |
| CPU/OS | Apple Silicon macOS is verified. Recipes target macOS 13+, Linux such as Ubuntu 22.04+, and Windows 10+ with PowerShell, but Intel macOS/Linux/Windows installs remain **untested**. Wheel availability varies by architecture; this is not a universal compatibility promise. |
| Network | Needed for initial packages and model downloads. Warm caches allow offline inference. |

The user chooses based on these requirements; the wizard does not inspect hardware, RAM, disk, or browser sessions.

Defaults are `small`, `cpu`, `int8`, batch size `8`, with no alignment or diarization. Segment timestamps are retained. In the reference measurements, small processed 69 seconds of English in 9.6 seconds on an Apple M5 Pro; slower CPUs and longer recordings take more time.

```dotenv
WATCH_WHISPER_BACKEND=whisperx
WATCH_WHISPERX_MODEL=small
WATCH_WHISPERX_DEVICE=cpu
WATCH_WHISPERX_COMPUTE_TYPE=int8
WATCH_WHISPERX_BATCH_SIZE=8
# WATCH_WHISPERX_LANGUAGE=es
# WATCH_WHISPERX_TIMEOUT=1800
```

The installer writes the absolute `WATCH_WHISPERX_BIN` path. The venv is `~/.cache/watch/whisperx-venv`, with a `.deps-ok` sentinel and resolved package list in `watch-install.json`. Interrupted installs without the sentinel are rebuilt safely. Model caches normally live under `~/.cache/huggingface` and `~/.cache/torch/hub`; uv also caches wheels and Python. These are outside the plugin, so updating the skill does not remove them.

For non-English audio, set the spoken-language hint (`WATCH_WHISPERX_LANGUAGE=es`, for example) or try `WATCH_WHISPERX_MODEL=large-v3` and rerun the installer. Large-v3 downloads about 2.9 GB and used about 6 GB peak process RAM in the reference measurement. Small can misidentify non-English speech without a hint. A caption translation request (`--sub-lang`) is never used as the spoken-language hint. WhisperX 3.8.6's JSON language is unreliable with alignment disabled, so auto-detection is reported as **unverified**.

Local inference has no default timeout; `WATCH_WHISPERX_TIMEOUT` accepts positive seconds. Failure or cancellation never switches to cloud transcription. CUDA is configurable but untested; MPS support is not promised. TorchCodec import warnings on newer FFmpeg are suppressed for this CLI-decoding path; do not downgrade FFmpeg just for that warning.

## Detail and focus

| Detail | Selection | Default cap |
|---|---|---|
| `transcript` | Transcript only; cue frames can be requested explicitly | No regular frames |
| `efficient` | Fast keyframes; uniform fallback when sparse | 50 |
| `balanced` | Scene changes; uniform fallback on nearly static clips | 100 |
| `token-burner` | Scene changes without a count cap; warning above 250 | Uncapped |

Use `WATCH_DETAIL` for the saved preference or `--detail` for one run. Best accuracy is usually with videos under 10 minutes or a focused interval:

```text
/watch video.mp4 --start 2:15 --end 2:45
/watch video.mp4 --detail efficient --max-frames 30
/watch video.mp4 --detail transcript --timestamps 1:05,2:30
```

Uniform sampling selects actual source frames across the range, reducing its rate to fit the remaining cap (at most 2 fps). Scene/keyframe selection detects candidates across the range, then samples to the cap. The last selected candidate need not be the last video frame; scene changes do not capture every event. Frame timestamps are source-relative, including focused and fractional seeks.

A 16×16 **RGB** thumbnail pass removes near-duplicates using mean channel difference. Use `--no-dedup` for subtle visual changes; tiny thumbnails cannot preserve every code edit. Default images are up to 512px wide and 1998px tall; `--resolution 1024` helps with on-screen text. Image cost depends on the host/model and frame dimensions.

After reading a transcript, the agent can pin “look here” moments with `--timestamps`. These consume the frame budget first. A caption-only pass may not download a video; in that case the cue pass uses the URL again. An audio-only download cannot supply cue frames.

## Captions, authentication, and partial results

Auto caption selection uses original-language evidence when available, preferring same-language manual captions before original ASR. It requests at most one track. Unknown provenance is labeled unknown. `--sub-lang CODE` / `WATCH_SUB_LANG` chooses an explicit language, which may be a translation.

Authentication is opt-in:

```text
/watch https://example.com/video --cookies /path/to/cookies.txt
/watch https://example.com/video --cookies-from-browser firefox
```

Use one cookie mechanism at a time, or save `WATCH_COOKIES_FILE` / `WATCH_COOKIES_FROM_BROWSER`. A cookie file is a read/write jar; yt-dlp may update it. Browser access can fail due to locked/encrypted stores, especially Chromium on Windows; Firefox is a possible alternative, not a guarantee. Watch never searches browser sessions automatically. Existing yt-dlp proxy, CA, runtime, and authentication configuration remains active when not explicitly overridden.

Fresh download directories prevent stale files from a failed source being reused. Media must complete successfully and report its final path; partial and merge-component files are rejected. Successful captions survive download, decoding, or probe failures. Reports distinguish unavailable evidence, no speech, and failed cloud chunks with missing time intervals. A silent requested interval never triggers fallback just because its captions are outside the range.

Cloud uploads use a 24,000,000-byte file budget with multipart and actual chunk checks. Local WhisperX takes the whole extracted audio file. No automatic provider/client/cookie cycling is performed.

## Updating and troubleshooting

Update the skill separately from its media tools. Claude Code marketplace auto-updates depend on your settings; use `/plugin update watch@claude-video` and reload. Other hosts can use `npx skills update watch -g`.

Update yt-dlp with its owning installer, then verify the same executable with `yt-dlp --version`:

- Homebrew: `brew upgrade yt-dlp`
- pipx: `pipx upgrade yt-dlp`
- Dedicated Python environment: `python -m pip install -U "yt-dlp[default,curl-cffi]"`
- winget: `winget upgrade --id yt-dlp.yt-dlp --exact`

`yt-dlp -U` is not a universal package-manager update command. See upstream [installation](https://github.com/yt-dlp/yt-dlp/wiki/Installation) and [EJS guidance](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

Ask the agent to run bundled `setup.py --json` for resolved paths/versions, JS-runtime presence, impersonation targets, and local-backend readiness. Diagnostics do not contact video services. EJS presence may remain unknown; it belongs to the actual yt-dlp distribution, not watch's Python. `setup.py --check` is fast, silent on success, and never imports Torch.

| Symptom | Next step |
|---|---|
| Command missing / wrong version | Check the resolved executable and reopen the agent after PATH changes. |
| Python opens the Store | Use an installed interpreter verified by `python --version` or `py -3 --version`. |
| FFmpeg option failure | Inspect the actual FFmpeg path; watch probes `-fps_mode` and retains advertised `-vsync` compatibility for older builds. |
| Missing JS runtime/EJS | Update the owning yt-dlp package and follow upstream Deno/EJS setup. |
| 403 / login challenge | Read the original error; use explicit authentication only if you have access. A 403 has no universal workaround. |
| 429 | Wait before retrying; the service is rate limiting requests. |
| Explicit hosted egress denial | Check the environment's network settings or use an accessible local source. Cloud ASR/cold model setup still need network access. |
| Certificate failure | Configure the trusted CA/proxy correctly; do not disable TLS verification. |
| Config parsing / encoding | Save as UTF-8 or BOM-marked UTF-16; diagnostic locations never echo credential values. |
| POSIX permissions warning | Set the config to mode 0600. Windows ACLs are not audited. Prefer a Linux-home config in WSL; Windows-mounted storage has different permission behavior. |
| Local install/inference failure | Rerun `setup.py --install-whisperx`; check the reported step, network access, disk/RAM requirements, and wheel compatibility. |

## Development and packaging

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest
.venv/bin/pytest -q
```

Tests use isolated config homes and synthesized FFmpeg media; no provider keys or live service calls. The offline yt-dlp integration test requires its CLI. CI runs on Linux, macOS, and Windows with real FFmpeg/ffprobe and gates the tag-triggered release job.

For a manual install, create the host's skill directory and symlink or copy the **whole `skills/watch/` folder**. Windows users can copy the folder or use a directory junction. Do not split `SKILL.md` from its sibling `scripts/` or add a duplicate command wrapper.

`bash skills/watch/scripts/build-skill.sh` builds `dist/watch.skill` from committed HEAD and refuses tracked dirty changes. Preview uncommitted code from a temporary staging directory. The bundle includes no planning documents, environments, or model weights. See [AGENTS.md](AGENTS.md) for repository structure and release rules.

## Data and cleanup

Local WhisperX processes audio on the machine; setup downloads packages/models from package and model hosts, with telemetry disabled. Warm-cache inference works offline, though upstream cache checks can still attempt network access. Cloud backends send extracted audio only to the selected provider. Video content is evidence, never executable instructions.

Watch creates a disposable run directory, including under any user-specified `--out-dir`. Cleanup removes that child only, preserving the user's directory and original media. Model environments/caches and private configuration are retained separately. No API keys are logged or included in reports.

MIT licensed. See [LICENSE](LICENSE).
