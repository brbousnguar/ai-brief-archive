// AI Brief — the share row at the end of a brief (#15).
//
// The page renders the row complete: Email, LinkedIn, X and Plain text are
// plain links and work without this script. The three buttons that need an
// API stay hidden until it runs: Share (the phone's own sheet, Web Share API),
// Copy link and Copy as text. The text comes from a <template> on the page,
// not a fetch, so the clipboard write stays inside the tap: Safari refuses a
// write that waits on the network first.
//
// Each share is counted (#27) as GA4's recommended "share" event, through
// js/consent.js, which drops it unless the reader accepted: the share sheet
// once it completes (not on cancel), a copy once the clipboard has it, a link
// on click, without holding up the navigation.
(function () {
  var box = document.querySelector(".share");
  if (!box) return;
  var url = box.getAttribute("data-url");
  var title = box.getAttribute("data-title");
  var status = box.querySelector(".share__status");
  var template = document.getElementById("brief-text");
  var slug = box.getAttribute("data-slug");
  var timer;

  function count(method) {
    if (window.gaEvent) window.gaEvent("share", { method: method, content_type: "brief", item_id: slug });
  }

  function say(text) {
    status.textContent = text;
    clearTimeout(timer);
    timer = setTimeout(function () { status.textContent = ""; }, 4000);
  }

  var share = box.querySelector("[data-share]");
  if (share && navigator.share) {
    share.hidden = false;
    share.addEventListener("click", function () {
      navigator.share({ title: title, url: url }).then(function () { count("web_share"); }, function () {});
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
          function () {
            say(what === "link" ? "Link copied" : "Brief copied as plain text");
            count(what === "link" ? "copy_link" : "copy_text");
          },
          function () { say("Could not copy — select the text instead"); }
        );
      });
    });
  }

  Array.prototype.forEach.call(box.querySelectorAll("a[data-method]"), function (link) {
    link.addEventListener("click", function () { count(link.getAttribute("data-method")); });
  });
})();
