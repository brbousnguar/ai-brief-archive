// AI Brief — the share row at the end of a brief (#15).
//
// The page renders the row complete: Email, LinkedIn, X and Plain text are
// plain links and work without this script. The three buttons that need an
// API stay hidden until it runs: Share (the phone's own sheet, Web Share API),
// Copy link and Copy as text. The text comes from a <template> on the page,
// not a fetch, so the clipboard write stays inside the tap: Safari refuses a
// write that waits on the network first.
(function () {
  var box = document.querySelector(".share");
  if (!box) return;
  var url = box.getAttribute("data-url");
  var title = box.getAttribute("data-title");
  var status = box.querySelector(".share__status");
  var template = document.getElementById("brief-text");
  var timer;

  function say(text) {
    status.textContent = text;
    clearTimeout(timer);
    timer = setTimeout(function () { status.textContent = ""; }, 4000);
  }

  var share = box.querySelector("[data-share]");
  if (share && navigator.share) {
    share.hidden = false;
    share.addEventListener("click", function () {
      navigator.share({ title: title, url: url }).catch(function () {});
    });
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    Array.prototype.forEach.call(box.querySelectorAll("[data-copy]"), function (button) {
      var what = button.getAttribute("data-copy");
      if (what === "text" && !template) return;
      button.hidden = false;
      button.addEventListener("click", function () {
        var text = what === "link" ? url : template.content.textContent.trim() + "\n";
        navigator.clipboard.writeText(text).then(
          function () { say(what === "link" ? "Link copied" : "Brief copied as plain text"); },
          function () { say("Could not copy — select the text instead"); }
        );
      });
    });
  }
})();
