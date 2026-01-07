/*\
title: $:/plugins/ykanchan/TWikiAppPlugin/syncadaptor.js
type: application/javascript
module-type: syncadaptor

PyWebView Sync Adaptor - stores tiddlers in SQLite via Python bridge

\*/

"use strict";

// Track PyWebView ready state
var pywebviewReady = false;
var pywebviewReadyTimeout = null;

// Debounce timer for HTML saves (prevents rapid saves during imports)
var htmlSaveTimer = null;
var HTML_SAVE_DELAY = 2000; // 2 seconds delay

// Check if PyWebView is already available (event may have fired before listener registered)
if (typeof pywebview !== "undefined" && pywebview.api && typeof pywebview.api.get_updated_tiddlers === "function") {
    pywebviewReady = true;
    console.log("[PyWebViewSyncAdaptor] PyWebView already available at script load");
}

// Listen for pywebviewready event
if (typeof window !== "undefined" && !pywebviewReady) {
    window.addEventListener("pywebviewready", function () {
        pywebviewReady = true;
        if (pywebviewReadyTimeout) {
            clearTimeout(pywebviewReadyTimeout);
            pywebviewReadyTimeout = null;
        }
        console.log("[PyWebViewSyncAdaptor] PyWebView is ready (event fired)");
    });

    // Set a timeout in case the event doesn't fire (5 seconds)
    pywebviewReadyTimeout = setTimeout(function () {
        if (!pywebviewReady) {
            console.warn("[PyWebViewSyncAdaptor] pywebviewready event timeout - checking if PyWebView is available anyway");
            // Check if PyWebView is actually available despite no event
            if (typeof pywebview !== "undefined" && pywebview.api && typeof pywebview.api.get_updated_tiddlers === "function") {
                pywebviewReady = true;
                console.log("[PyWebViewSyncAdaptor] PyWebView is available (fallback check)");
            } else {
                console.error("[PyWebViewSyncAdaptor] PyWebView API not available after timeout");
            }
        }
        pywebviewReadyTimeout = null;
    }, 5000);
}

function PyWebViewSyncAdaptor(options) {
    this.wiki = options.wiki;
    this.logger = new $tw.utils.Logger("PyWebViewSyncAdaptor");
}

PyWebViewSyncAdaptor.prototype.name = "pywebview";

PyWebViewSyncAdaptor.prototype.supportsLazyLoading = true;

PyWebViewSyncAdaptor.prototype.isReady = function () {
    return pywebviewReady &&
        typeof pywebview !== "undefined" &&
        pywebview.api &&
        typeof pywebview.api.get_updated_tiddlers === "function";
};

PyWebViewSyncAdaptor.prototype.getUpdatedTiddlers = function (syncer, callback) {
    var self = this;

    if (!this.isReady()) {
        return callback("PyWebView API not available");
    }

    // Get the last sync time from the syncer
    var lastSyncTime = syncer.lastSyncTime || null;

    // Get list of currently loaded tiddler titles from TiddlyWiki
    // This is used for deletion detection - any tiddler in SQLite but not in this list was deleted
    // getTiddlers() returns all non-shadow, non-system tiddlers by default
    var currentTiddlers = $tw.wiki.getTiddlers();

    pywebview.api.get_updated_tiddlers(lastSyncTime, currentTiddlers)
        .then(function (result) {
            // Result format: {modifications: [titles], deletions: [titles]}
            self.logger.log("Retrieved updates: " + result.modifications.length + " modifications, " + result.deletions.length + " deletions");

            // Update last sync time
            syncer.lastSyncTime = new Date().toISOString();

            callback(null, result);
        })
        .catch(function (err) {
            self.logger.log("Error getting updated tiddlers:", err);
            callback(err);
        });
};

PyWebViewSyncAdaptor.prototype.loadTiddler = function (title, callback) {
    var self = this;

    if (!this.isReady()) {
        return callback("PyWebView API not available");
    }

    pywebview.api.get_tiddler(title)
        .then(function (tiddlerJson) {
            if (tiddlerJson) {
                self.logger.log("Loaded tiddler:", title);
                // Parse JSON string to object for TiddlyWiki
                var tiddler = JSON.parse(tiddlerJson);
                callback(null, tiddler);
            } else {
                self.logger.log("Tiddler not found:", title);
                callback(null, null);
            }
        })
        .catch(function (err) {
            self.logger.log("Error loading tiddler:", title, err);
            callback(err);
        });
};

PyWebViewSyncAdaptor.prototype.getTiddlerInfo = function (tiddler) {
    // Return metadata for all tiddlers to track what's been synced
    // This helps with deletion detection
    return {
        synced: true
    };
};

PyWebViewSyncAdaptor.prototype.saveTiddler = function (tiddler, callback, options) {
    var self = this;

    if (!this.isReady()) {
        return callback("PyWebView API not available");
    }

    options = options || {};
    var title = tiddler.fields.title;
    var isSystemTiddler = title.startsWith("$:/");

    // Skip HTML save for StoryList (UI state that changes during navigation)
    var shouldTriggerHtmlSave = isSystemTiddler && title !== "$:/StoryList";

    // Use TiddlyWiki's built-in JSON serialization
    // Send as JSON string directly - no need to parse and re-serialize
    var tiddlerJson = this.wiki.getTiddlerAsJson(title);

    self.logger.log("Saving tiddler:", title, isSystemTiddler ? "(system)" : "");

    pywebview.api.put_tiddler(title, tiddlerJson)
        .then(function (response) {
            self.logger.log("Saved tiddler:", title);

            // If system tiddler (excluding StoryList), trigger debounced HTML save
            if (shouldTriggerHtmlSave) {
                // Clear any existing timer
                if (htmlSaveTimer) {
                    clearTimeout(htmlSaveTimer);
                }

                // Set new timer - only triggers if no more saves within delay period
                htmlSaveTimer = setTimeout(function () {
                    self.logger.log("System tiddler(s) modified - triggering HTML save (debounced)");
                    $tw.rootWidget.dispatchEvent({ type: "tm-save-wiki" });
                    htmlSaveTimer = null;
                }, HTML_SAVE_DELAY);
            }

            callback(null);
        })
        .catch(function (err) {
            self.logger.log("Error saving tiddler:", title, err);
            callback(err);
        });
};

PyWebViewSyncAdaptor.prototype.deleteTiddler = function (title, callback, options) {
    var self = this;

    if (!this.isReady()) {
        return callback("PyWebView API not available");
    }

    pywebview.api.delete_tiddler(title)
        .then(function (response) {
            self.logger.log("Deleted tiddler:", title);
            callback(null);
        })
        .catch(function (err) {
            self.logger.log("Error deleting tiddler:", title, err);
            callback(err);
        });
};

if ($tw.browser) {
    exports.adaptorClass = PyWebViewSyncAdaptor;
}
