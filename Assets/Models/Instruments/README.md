# Instrument replacements — second art pass

Original modeled assets for Drumsmith, created sequentially: Drumkit, Guitar, Bass, MicStand. The mic stand, guitar, bass drumkit and keyboard now replace the procedural instrument meshes in `Band.cpp`.

Each folder contains an editable `.blend`, `.fbx`, triangulated `.obj` with `.mtl`, transparent `preview.png`, and a manifest with object names, parent relationships, local positions and triangle count. Materials use solid colors and metallic/roughness values; no external textures are required. These are detailed source assets, not yet draw-call/LOD optimized or validated in the game renderer.

- **Drumkit:** red lacquer five-piece kit, chrome hoops/lugs, four cymbal stations including hi-hat, tripod hardware, kick and hi-hat pedals, throne. Named drum parents and cymbal origins support later animation hookup.
- **Guitar:** red single-cutaway six-string, small ivory pickguard, two humbuckers, fretted rosewood board, maple neck, inlays and tuning hardware.
- **Bass:** petrol blue four-string, black pickguard and longer neck, matching hardware. Both necks extend into a seated heel inside the body; the original nut positions and hand targets are retained.
- **Keyboard:** 61 individual keys, graphite chassis with wooden end cheeks, LCD, encoders, faders, double X stand and sustain pedal. Keys remain at the existing performer hand height.
- **MicStand:** weighted circular base, telescoping shaft, height clutch, clip, microphone grille and trailing cable.

## Coordinates and integration

The authoring scene and OBJ vertices use metres, **Y up**, **+Z toward audience**. This deliberately differs from Blender's normal Z-up authoring convention. Stringed instruments are centered at the body, with neck along -X and face +Z, following `Band::BuildStringed`; neck spans are 0.62 m (guitar) and 0.86 m (bass). Drumkit root is floor origin near the drummer; mic stand is floor-centered with a shaft height of 1.47 m. FBX uses Blender's standard Y-up export conversion: respect the FBX axis metadata when importing; use OBJ for direct game-coordinate vertices.

Runtime exports live in `Runtime/`. They pre-flip Z and reverse polygon winding to compensate for the engine's Assimp `ConvertToLeftHanded` import. Use these files in game; the original OBJ files are authoring exports. All runtime metadata disables unit conversion because vertices are already in metres.

Drum shells and cymbals are exported separately at local animation origins, with cymbal grooves, felt and wingnuts included in each cymbal mesh. `Band::BuildDrums` places heads at the existing strike targets and keeps hit squash / cymbal wobble. Stands, throne and pedals are a stationary hardware model; pedals follow the existing foot targets. Guitar and bass retain the old body pivot and neck lengths for hands and neck cameras. Mic stands retain existing placement and height scaling; their imported grille points toward the performer.

Runtime meshes are joined per rigid assembly, retaining material slots. Source files retain editable individual objects. No LODs or painted textures are included. Material appearance and performer clearances still need an in-game visual check.

## Rebuild one asset

From the repository root, with Blender 5.2:

```sh
blender -b --python Tools/InstrumentAssets/build.py -- Drumkit
blender -b --python Tools/InstrumentAssets/build.py -- Guitar
blender -b --python Tools/InstrumentAssets/build.py -- Bass
blender -b --python Tools/InstrumentAssets/build.py -- MicStand
blender -b --python Tools/InstrumentAssets/build.py -- Keyboard
```

Each command rebuilds only its named asset and studio preview. The previews are actual geometry rendered in Blender Cycles.

After rebuilding authoring assets, regenerate the runtime exports:

```sh
blender -b --python Tools/InstrumentAssets/prepare_runtime.py
```
