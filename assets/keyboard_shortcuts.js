document.addEventListener("keydown", function (e) {
    // Ctrl+K (or Cmd+K on Mac) focuses and selects the ticker input
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault(); // Prevent browser default (e.g., Chrome address bar)
        var tickerInput = document.getElementById("ticker-input");
        if (tickerInput) {
            tickerInput.focus();
            tickerInput.select(); // Select all existing text
        }
    }


});