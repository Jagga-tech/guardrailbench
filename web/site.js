// Small extras on top of plain HTML. Every page works without this file.
(function () {
  'use strict';
  var menus = Array.prototype.slice.call(document.querySelectorAll('.menu details'));

  // Nav dropdowns: one open at a time; close on outside click or Escape.
  menus.forEach(function (d) {
    d.addEventListener('toggle', function () {
      if (d.open) menus.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });
  document.addEventListener('click', function (e) {
    menus.forEach(function (d) { if (d.open && !d.contains(e.target)) d.open = false; });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    menus.forEach(function (d) {
      if (d.open) { d.open = false; d.querySelector('summary').focus(); }
    });
  });

  // Citations: format tabs and copy buttons. Without script, all formats show stacked.
  Array.prototype.forEach.call(document.querySelectorAll('.cite'), function (block) {
    var tabs = Array.prototype.slice.call(block.querySelectorAll('[role="tab"]'));
    var panes = Array.prototype.slice.call(block.querySelectorAll('[role="tabpanel"]'));
    function show(i, focus) {
      tabs.forEach(function (t, j) {
        t.setAttribute('aria-selected', i === j);
        t.tabIndex = i === j ? 0 : -1;
        panes[j].hidden = i !== j;
      });
      if (focus) tabs[i].focus();
    }
    tabs.forEach(function (t, i) {
      t.hidden = false;
      t.addEventListener('click', function () { show(i); });
      t.addEventListener('keydown', function (e) {
        var j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
        if (j === undefined) return;
        e.preventDefault();
        show((j + tabs.length) % tabs.length, true);
      });
    });
    block.querySelector('.tabs').hidden = false;
    show(0);
  });

  Array.prototype.forEach.call(document.querySelectorAll('.copy'), function (btn) {
    btn.hidden = false;
    btn.addEventListener('click', function () {
      var text = btn.parentNode.querySelector('pre').textContent;
      var done = function (msg) {
        btn.textContent = msg;
        setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done('Copied'); }, function () { done('Copy failed'); });
      } else {
        // ponytail: execCommand fallback for http/file previews; drop once Clipboard API is everywhere we care about
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        document.body.removeChild(ta);
        done(ok ? 'Copied' : 'Copy failed');
      }
    });
  });
})();
