// Renders the home-page leaderboard from data/leaderboard.json.
// Without script (or if the file cannot load) the static empty table in index.html stays.
(function () {
  'use strict';
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.lb [role="tab"]'));
  var panel = document.getElementById('lb-panel');
  var desc = document.getElementById('lb-desc');
  var table = document.getElementById('lb-table');
  var cpSelect = document.getElementById('f-cp');
  var readingSet = document.getElementById('f-reading');
  if (!tabs.length || !table) return;

  var BADGES = {
    open_source: ['open source', 'badge--open'],
    maintainer_run: ['maintainer run', 'badge--run'],
    self_reported: ['self-reported', 'badge--self'],
    affiliated: ['affiliated', 'badge--aff'],
    baseline: ['baseline', 'badge--base']
  };
  var EMPTY = 'No published results yet — first results follow legal review and outside review of the hidden split.';
  var state = { board: tabs[0].dataset.board, cp: 'all', reading: 'strict', data: null };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function safeUrl(u) { return /^https:\/\//.test(u || '') ? u : null; }
  function pct(v) { return typeof v === 'number' ? (100 * v).toFixed(1) : null; }
  function num(v, extra) { return v == null ? '<td class="num">—</td>' : '<td class="num">' + v + (extra || '') + '</td>'; }

  function productCell(r) {
    var name = safeUrl(r.site) ? '<a href="' + esc(r.site) + '">' + esc(r.product) + '</a>' : esc(r.product);
    var badges = (r.badges || []).filter(function (b) { return BADGES[b]; }).map(function (b) {
      return '<span class="badge ' + BADGES[b][1] + '">' + BADGES[b][0] + '</span>';
    }).join('');
    return '<th scope="row"><span class="prod">' + name + (badges ? '<span class="badges">' + badges + '</span>' : '') + '</span></th>';
  }
  function tailCells(r) {
    var logs = safeUrl(r.logs) ? '<a href="' + esc(r.logs) + '">logs</a>' : '—';
    return '<td>' + esc(r.organisation) + '</td><td>' + esc(r.version) + '</td><td class="num">' + esc(r.date) + '</td><td>' + logs + '</td>';
  }

  var KINDS = {
    detection: {
      head: function () {
        return ['Product', 'Pair score<small>' + state.reading + '</small>', 'Unsure', 'Detection<small>' + state.reading + '</small>', 'False block<small>' + state.reading + '</small>', 'Organisation', 'Version', 'Date', 'Logs'];
      },
      key: function (r) { var m = (r.by_checkpoint || {})[state.cp]; return m && m[state.reading] ? -m[state.reading].pair_score : Infinity; },
      row: function (r) {
        var m = (r.by_checkpoint || {})[state.cp];
        if (!m) return productCell(r) + '<td class="num"><span class="nc">not claimed</span></td><td class="num">—</td><td class="num">—</td><td class="num">—</td>' + tailCells(r);
        var x = m[state.reading] || {};
        var ci = x.ci ? '<span class="ci">' + pct(x.ci[0]) + '–' + pct(x.ci[1]) + '</span>' : '';
        return productCell(r) + num(pct(x.pair_score), ci) + num(pct(m.unsure)) + num(pct(x.detection)) + num(pct(x.false_block)) + tailCells(r);
      }
    },
    reliability: {
      head: function () {
        return ['Product', 'Flip rate', 'Instability<small>worst variant</small>', 'p95 latency<small>32 workers</small>', 'Long-input detection<small>vs control false block</small>', 'Errors', 'Organisation', 'Version', 'Date', 'Logs'];
      },
      key: function (r) { var f = (r.flip_rate || {})[state.cp]; return typeof f === 'number' ? f : Infinity; },
      row: function (r) {
        var inst = r.instability_worst || {};
        var li = r.long_input || {};
        var lic = li.detection == null ? null : pct(li.detection) + ' / ' + pct(li.control_false_block);
        var lin = li.chars ? '<span class="ci">at ' + esc(li.chars.toLocaleString('en')) + ' chars</span>' : '';
        return productCell(r) + num(pct((r.flip_rate || {})[state.cp])) +
          num(pct(inst.value), inst.variant ? '<span class="ci">' + esc(inst.variant) + '</span>' : '') +
          num(r.p95_ms_32 == null ? null : esc(r.p95_ms_32) + ' ms') + num(lic, lin) +
          num(r.errors ? pct(r.errors.rate) : null, r.errors ? '<span class="ci">' + esc(r.errors.count) + '</span>' : '') + tailCells(r);
      }
    }
  };

  function render() {
    var tab = tabs.filter(function (t) { return t.dataset.board === state.board; })[0];
    var board = state.data ? state.data.boards[state.board] : null;
    var kind = KINDS[(board && board.kind) || tab.dataset.kind];
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', on);
      t.tabIndex = on ? 0 : -1;
    });
    panel.setAttribute('aria-labelledby', tab.id);
    desc.textContent = tab.dataset.desc;
    readingSet.disabled = tab.dataset.kind === 'reliability';

    var cols = kind.head();
    var cpLabel = cpSelect.options[cpSelect.selectedIndex].text;
    var caption = tab.textContent + ', ' + cpLabel.toLowerCase() + (readingSet.disabled ? '' : ', ' + state.reading + ' reading');
    var rows = ((board && board.results) || []).slice().sort(function (a, b) { return kind.key(a) - kind.key(b); });
    var body = rows.length ? rows.map(function (r) { return '<tr>' + kind.row(r) + '</tr>'; }).join('') :
      '<tr class="empty"><td colspan="' + cols.length + '"><div><span class="empty-title">Nothing published</span><p>' + EMPTY + '</p>' + (tab.dataset.empty ? '<p>' + tab.dataset.empty + '</p>' : '') + '</div></td></tr>';
    table.innerHTML = '<caption class="visually-hidden">' + esc(caption) + '</caption><thead><tr>' +
      cols.map(function (c) { return '<th scope="col">' + c + '</th>'; }).join('') + '</tr></thead><tbody>' + body + '</tbody>';
  }

  function select(board, focus) {
    state.board = board;
    try { history.replaceState(null, '', '#' + board); } catch (e) { /* file:// or sandboxed */ }
    render();
    if (focus) tabs.filter(function (t) { return t.dataset.board === board; })[0].focus();
  }

  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { select(t.dataset.board); });
    t.addEventListener('keydown', function (e) {
      var j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (j === undefined) return;
      e.preventDefault();
      select(tabs[(j + tabs.length) % tabs.length].dataset.board, true);
    });
  });
  cpSelect.addEventListener('change', function () { state.cp = cpSelect.value; render(); });
  readingSet.addEventListener('change', function (e) { state.reading = e.target.value; render(); });

  var fromHash = location.hash.slice(1);
  if (tabs.some(function (t) { return t.dataset.board === fromHash; })) state.board = fromHash;
  state.cp = cpSelect.value;
  var checked = readingSet.querySelector('input:checked');
  if (checked) state.reading = checked.value;
  render();

  fetch('data/leaderboard.json', { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { state.data = d; render(); })
    .catch(function () { /* keep the empty state already rendered */ });
})();
