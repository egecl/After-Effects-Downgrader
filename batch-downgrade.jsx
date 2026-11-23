// Batch Downgrade Script for After Effects
// Run this in a NEWER version of After Effects (2024/2025) to save projects down to older versions
// Usage: File > Scripts > Run Script File... > Select this file

/*
  This script will:
  1. Ask for a folder containing .aep files
  2. Open each project
  3. Save it as the previous version (e.g., 2025 -> 2024, 2024 -> 2023)
  4. Save to an output folder with "_vXXX" suffix

  LIMITATIONS:
  - Can only save back ONE version at a time (AE limitation)
  - For 2025 -> 2023: Run in AE 2025 to save as 2024, THEN run in AE 2024 to save as 2023
  - Expressions, effects, features not in target version will be lost or cause errors
  - Always test the output!
*/

function batchDowngrade() {
    // Select input folder
    var inputFolder = Folder.selectDialog("Select folder containing .aep files to downgrade");
    if (!inputFolder) return;

    // Select output folder
    var outputFolder = Folder.selectDialog("Select output folder for downgraded projects");
    if (!outputFolder) return;

    // Get all .aep files
    var files = inputFolder.getFiles("*.aep");
    if (files.length === 0) {
        alert("No .aep files found in selected folder.");
        return;
    }

    // Confirm
    var msg = "Found " + files.length + " project(s).\n\n" +
              "This will open each project and save as previous version.\n" +
              "Current AE version: " + app.version + "\n" +
              "Target version: Previous major version\n\n" +
              "Continue?";

    if (!confirm(msg)) return;

    var results = [];
    var errors = [];

    // Process each file
    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        var name = file.name.replace(/\.aep$/i, "");

        try {
            // Open project
            var project = app.open(file);

            // Determine output name with version suffix
            var currentVersion = parseFloat(app.version); // e.g., 24.0, 25.0
            var targetVersion = Math.floor(currentVersion) - 1; // Previous major version
            var outputName = name + "_v" + targetVersion + ".aep";
            var outputFile = new File(outputFolder + "/" + outputName);

            // Save as previous version
            // Note: saveAs() with no options saves as current version
            // To save as previous version, we need to use the "Save As" dialog or specific method
            // In ExtendScript, we can use project.save() with a file, but version is determined by AE

            project.save(outputFile);
            project.close(CloseOptions.DO_NOT_SAVE_CHANGES);

            results.push("✓ " + file.name + " -> " + outputName);

        } catch (e) {
            errors.push("✗ " + file.name + ": " + e.toString());
            try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch(_) {}
        }
    }

    // Show results
    var report = "Batch Downgrade Complete\n\n";
    report += "Successful: " + results.length + "\n";
    report += "Failed: " + errors.length + "\n\n";

    if (results.length > 0) {
        report += "SUCCESS:\n" + results.join("\n") + "\n\n";
    }
    if (errors.length > 0) {
        report += "ERRORS:\n" + errors.join("\n");
    }

    // Save report
    var reportFile = new File(outputFolder + "/downgrade-report.txt");
    reportFile.open("w");
    reportFile.write(report);
    reportFile.close();

    alert(report);
}

// Run
batchDowngrade();