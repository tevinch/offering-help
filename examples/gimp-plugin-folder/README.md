# Find GIMP's plug-in folder and install Batcher

In GIMP 3.2.6, **Plug-ins is a child of Folders in the Preferences sidebar**. The Folders group starts collapsed. Clicking the word Folders opens the temporary/swap directory settings; expand the group to reach its other pages.

This walkthrough covers Batcher **1.2.10**, which supports GIMP 3.2. It uses an additional personal folder so the existing plug-in search paths can stay in place.

## Find the Plug-ins page

1. Open **Edit → Preferences**. On macOS, use **GIMP → Settings/Preferences**.
2. In the left sidebar, scroll to **Folders** and click the small arrow beside it to expand its children.
3. Scroll through those children and select **Plug-ins**. The right-hand page should be titled **Plug-in Folders**.

## Add a personal folder

1. In your file manager, create a folder you can write to, for example a folder named `GIMP-plug-ins` inside Documents. GIMP's path setting does not create the directory for you.
2. On the **Plug-in Folders** page, click the blank-page button whose tooltip is **Add a new folder**.
3. Use the folder chooser button beside the path entry to choose the directory you just created.
4. Confirm that it appears as an **additional row** and that all previously listed paths remain. Starting with Add a new folder clears the current selection; editing a selected row instead can replace that row's path.

The folder name is your choice. Add the parent search folder, such as `GIMP-plug-ins`, rather than the inner `batcher` folder shown below.

## Copy Batcher and restart

1. Download `batcher-1.2.10.zip` from the [Batcher 1.2.10 release](https://github.com/kamilburda/batcher/releases/tag/1.2.10) and extract it.
2. Copy the **complete `batcher` folder** from the archive into the personal search folder. Keep all of its files and subfolders together:

   ```text
   GIMP-plug-ins/             ← the directory added in Preferences
   └── batcher/
       ├── batcher.py
       └── ...other Batcher files and folders...
   ```

3. Close Preferences and restart GIMP. Look for **File → Batch Convert…**.
4. For a first check, add two image copies with different filenames to Batch Convert. Choose a new, empty output directory and an output format such as PNG, then press **Run**. The expected result is two exported images in that output directory; open them to check their content.

If Plug-ins is still absent after expanding Folders, or Batch Convert does not appear after restarting, the next useful details are your OS, GIMP version/build and installation source. For the Windows installer from gimp.org, Batcher requires Python plug-in support to be enabled; the Microsoft Store edition enables it automatically. Batcher's installation guide currently lists the Linux Snap edition as unsupported.

## Sources and checked scope

- [GIMP 3.2 Data Folders](https://docs.gimp.org/3.2/en/gimp-prefs-folders-data.html): directory list, chooser, existing-directory requirement and search paths.
- [GIMP 3.2.6 Preferences source](https://github.com/GNOME/gimp/blob/GIMP_3_2_6/app/dialogs/preferences-dialog.c#L3538-L3740): Folders parent, Plug-ins child and initial collapse.
- [GIMP 3.2.6 path editor source](https://github.com/GNOME/gimp/blob/GIMP_3_2_6/libgimpwidgets/gimppatheditor.c#L621-L653): Add a new folder clears the selected row; [path changes append or replace a row](https://github.com/GNOME/gimp/blob/GIMP_3_2_6/libgimpwidgets/gimppatheditor.c#L766-L815).
- [Batcher 1.2.10 installation instructions](https://github.com/kamilburda/batcher/blob/1.2.10/docs/sections/Installation.md) and [Batch Convert usage](https://github.com/kamilburda/batcher/blob/1.2.10/docs/sections/Usage.md#batch-image-conversion).

Checked against the versioned source and documentation above. The GIMP GUI, OS-specific installation and actual conversion have not been validated here; the two-image check is a step for the person installing it.

## Optional coffee

This example is free. If it saved you time, an optional coffee is appreciated.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
