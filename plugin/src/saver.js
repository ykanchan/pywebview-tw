/*\
title: $:/plugins/ykanchan/TWikiAppPlugin/saver.js
type: application/javascript
module-type: saver

Multi-Wiki Saver Module for the PyWebView bridge

\*/

"use strict";

/*
Select the appropriate saver module and set it up
*/
var PyWebViewSaver = function (wiki) {
    this.wiki = wiki;
};


PyWebViewSaver.prototype.save = function (text, method, callback, options) {
    try {

        const payload = {
            action: "tiddlywiki-save",
            text: text,
            timestamp: new Date().toISOString()
        };

        pywebview.api.save(payload).then(() => {
            if (typeof callback === "function") {
                callback(null);
            }
        }
        )

        return true;

    } catch (e) {
        console.error("PyWebView customSaver error", e);
        if (typeof callback === "function") {
            callback(e);
        }
        return false;
    }
};


/*
Information about this saver
*/
PyWebViewSaver.prototype.info = {
    name: "PyWebViewSaver",
    priority: 10000,
    capabilities: ["save", "autosave"]
};

/*
Static method that returns true if this saver is capable of working
*/
exports.canSave = function (wiki) {
    // return (typeof pywebview !== "undefined" && pywebview.api && typeof pywebview.api.save === "function");
    return true
};

/*
Create an instance of this saver
*/
exports.create = function (wiki) {
    return new PyWebViewSaver(wiki);
};
