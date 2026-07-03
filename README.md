# PlasmaCardsAR-Content

Remote model bundles for the PlasmaCardsAR app, served via GitHub Pages.

The app (Unity Addressables) loads from:
`https://rzhu98-hub.github.io/PlasmaCardsAR-Content/[BuildTarget]`

Folders:
- `StandaloneWindows64/` — bundles for Windows editor/desktop testing
- `iOS/` — bundles for the iPhone build (built on the Mac with build target iOS)

To update content: rebuild Addressables in Unity (Build > New Build > Default
Build Script), copy the new files from `PlasmaCardsAR/ServerData/<platform>/`
here, commit, push. Apps pick up changes via the remote catalog without an
App Store update.
