# Three-source studio

A local Streamlit dashboard for controlled, raw synthetic sources. No analytical pipeline is included.

## First walkthrough

1. Start the app using the commands below, or run `./start.ps1` in PowerShell.
2. In **Image**, select a flavor and switch between one, two, and three scoops. Notice that the cone and canvas do not shrink as scoops are added.
3. In **Audio**, choose a low, middle, or high tone and press the player's play button. This choice is independent of the image.
4. In **Text**, select the flavor and read the story. Its wording remains fixed except for the five flavor mentions.
5. Read the selection summary below the tabs. Press **Save event** to copy that exact combination into its own folder, then download its ZIP. You can also download any source individually.

This gives you actual files to inspect and later feed into preprocessing. It does not yet calculate representations or tell you whether sources agree.

## What each part does

| File or folder | Purpose |
|---|---|
| `generator.py` | The source recipes and event export logic, independent of Streamlit. |
| `app.py` | Controls, previews, download buttons, and saving the current selection. |
| `data/library/` | The nine stored images, three tones, and three stories. |
| `data/events/` | Locally saved snapshots; excluded from Git. |
| `tests/test_generator.py` | Checks that the sources obey the intended rules and the UI can change controls. |
| `requirements.txt` | Exact top-level library versions used for the verified build. |

## Installing on another machine

Use Python 3.13 (the version used for this build). In this project folder, create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python`; activation is optional.

## Run

From this directory, with Python and the dependencies in `requirements.txt` installed:

```powershell
python generator.py
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. The included source library is already generated; regenerating it is deterministic.

## Sources and controls

- **Image:** nine PNGs, three flavors × one, two, or three scoops. A fixed 512 × 640 light-gray canvas reserves room for three scoops. The cone and 134-pixel scoop diameter are fixed. Scoops stack upward with slight overlap; exact flavor-color area increases with scoop count. No whole-scene resizing, lettering, or truck artwork.
- **Audio:** one pure sine tone per ten-second WAV: low 220 Hz, middle 440 Hz, high 880 Hz. Mono 16 kHz, signed 16-bit PCM, peak amplitude 20% of full scale. All clips share identical 10 ms fades to prevent endpoint clicks. Tone selection is independent of flavor.
- **Text:** a fixed story under 100 words, with five occurrences of the selected flavor. Only those substitutions vary. Preview includes word count.

`data/library` holds the stored source assets and is never modified by the dashboard. Downloads expose individual sources. **Save event** copies the current selections into `data/events/<browser session>/<event ID>` with separate `image.png`, `audio.wav`, `text.txt`, and `manifest.json`; the ZIP contains the same files. Each browser session has its own export directory, and each save gets a new event ID. All three sources share the manifest's event ID and UTC creation timestamp. This is a snapshot time, not a simulation clock or temporal analysis. Generator settings in the manifest are ground truth for later evaluation; do not silently feed them into future discovery models.

Image and text flavors may intentionally disagree. Audio has no flavor mapping. A saved event is an immutable snapshot from the dashboard's perspective; subsequent control changes affect only the current preview.

## Verification

```powershell
python -m unittest discover -s tests -v
```

Checks cover increasing pixel area and fixed scene geometry, WAV format/duration/frequency/amplitude, controlled story substitution, event export consistency, and Streamlit rendering/control changes. This build intentionally defers SQL, TF-IDF, audio feature extraction, clustering, fusion, model training, daily simulation, and calibration.

## Making your next change

For a story, color, or tone change, edit the relevant constant or function in `generator.py`, run `python generator.py` to refresh the stored library, then run the tests. Refresh the dashboard to view it. Existing saved events keep their old copies. For a label, layout, or control change, edit `app.py` and rerun the dashboard; Streamlit rereads the UI code when it reruns. Keep future preprocessing in a separate module that reads the source files so the generator remains simple.

## Deployment handoff

The folder is ready for a GitHub repository and Streamlit Community Cloud, but this README does not claim a deployment exists. Include `data/library` in the repository; exclude event exports and secrets using the supplied `.gitignore`.

Once the repository is available in your GitHub account, sign into Streamlit Community Cloud, create an app from that repository, choose branch `main`, use `app.py` as the entrypoint, and select Python 3.13 in advanced settings. The root `requirements.txt` supplies dependencies. Choose an available app subdomain. The resulting `streamlit.app` address is the shareable link, unlike the local address above. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

On a hosted demo, event folders are server-local working storage, not a durable dataset archive. Download event ZIPs to keep them. No credentials or API keys are needed by this generator. Future code changes go into the GitHub repository; the connected hosted app can then update from those changes.

Git keeps named checkpoints of your code. After making and testing a change, inspect it with `git diff`, stage the intended files with `git add`, and create a checkpoint with `git commit -m "Describe the change"`. Once an authenticated remote is connected, `git push` sends that checkpoint to GitHub. The connected Community Cloud app follows its configured branch, so updates can use the same app link. This local delivery has a Git repository initialized on `main`, but no remote or commits yet.
