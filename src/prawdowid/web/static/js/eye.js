// Prawdowid - obserwujace oko.
//
// Stany:
//   idle    - po wejsciu na strone i po odpowiedzi: patrzy na nas, lekko zmruzone, czasem mruga.
//   typing  - gdy piszemy w polu pytania: otwiera sie i sledzi kursor tekstowy.
//   waiting - od wyslania pytania do odpowiedzi: na wprost -> lewo -> prawo -> na wprost -> mrugniecie, w petli.
//
// Oko rysuja dwie rzeczy w SVG: ksztalt powiek (#eye-lids, uzyty jako maska i obrys)
// oraz przesuniecie teczowki (.eye__iris). Skrypt co klatke wylicza oba z aktualnego stanu.
(function () {
  'use strict';

  var svg = document.querySelector('.eye__svg');
  var lids = document.getElementById('eye-lids');
  var iris = svg && svg.querySelector('.eye__iris');
  var input = document.getElementById('ask-text');
  var form = document.querySelector('.ask');
  var answer = document.getElementById('answer');
  var figure = document.querySelector('.eye');
  if (!svg || !lids || !iris) return;

  // ---- Geometria (jednostki viewBox 0 0 400 220) ----
  var LID_CLOSED = 146;  // punkt kontrolny obu powiek przy zamknietym oku
  var UP_OPEN = -30;     // gorna powieka w pelni otwarta
  var LOW_OPEN = 250;    // dolna powieka w pelni otwarta
  var MAX_X = 92;        // jak daleko teczowka moze odjechac w bok
  var MAX_Y = 26;        // jak daleko w gore/dol

  // Otwarcie powiek dla stanu: 1 = w pelni otwarte, 0 = zamkniete.
  var POSE = {
    idle:    { up: 0.72, low: 0.8 },  // lekko zmruzone
    typing:  { up: 1,    low: 1 },
    waiting: { up: 1,    low: 1 }
  };

  // Rozgladanie sie podczas czekania: [sekunda cyklu, x, y]. Miedzy punktami - szybki ruch z wyhamowaniem.
  var CYCLE = 9;
  var LOOK = [[0, 0, 0], [1.4, 0, 0], [1.65, -MAX_X, 0], [3.1, -MAX_X, 0],
              [3.45, MAX_X, 0], [5.0, MAX_X, 0], [5.3, 0, 0], [CYCLE, 0, 0]];
  var WAIT_BLINK_AT = 6.55;

  var mode = 'idle';
  var modeStart = now();
  var cur = { x: 0, y: 0, up: POSE.idle.up, low: POSE.idle.low };
  var gaze = { x: 0, y: 0 };      // cel wzroku w trybie pisania
  var blinkStart = -1e9;
  var nextBlink = now() + 2500;
  var lastWaitT = 0;
  var last = now();
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  function now() { return performance.now(); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function easeIn(t) { return t * t * t; }

  // Mrugniecie: zamkniecie ~110 ms, chwila zamkniete, otwarcie ~250 ms. Zwraca 1 (otwarte) .. 0 (zamkniete).
  function blinkFactor(ms) {
    if (ms < 0 || ms > 400) return 1;
    if (ms < 110) return 1 - easeIn(ms / 110);
    if (ms < 150) return 0;
    return easeOut((ms - 150) / 250);
  }

  function lookAt(t) {
    for (var i = 1; i < LOOK.length; i++) {
      if (t <= LOOK[i][0]) {
        var a = LOOK[i - 1], b = LOOK[i];
        var k = easeOut((t - a[0]) / (b[0] - a[0] || 1));
        return { x: lerp(a[1], b[1], k), y: lerp(a[2], b[2], k) };
      }
    }
    return { x: 0, y: 0 };
  }

  // ---- Kolor oka (CSS: .eye[data-mood]) ----
  // Pisanie i czekanie - zolte; potem kolor wyniku (positive / negative / neutral) az do
  // kolejnego pisania; bez wyniku - niebieskie (idle).
  var resultMood = null;

  function applyMood() {
    if (!figure) return;
    figure.setAttribute('data-mood', mode === 'idle' ? (resultMood || 'idle') : 'busy');
  }

  function setMode(m) {
    if (m !== mode) {
      mode = m;
      modeStart = now();
      lastWaitT = 0;
      if (reduce.matches) render(1);
    }
    applyMood();
  }

  // ---- Pozycja kursora tekstowego w polu (kopia pola w ukrytym divie) ----
  var mirror = document.createElement('div');
  var COPY = ['boxSizing', 'width', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
              'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
              'fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'letterSpacing', 'lineHeight',
              'textTransform', 'wordSpacing', 'tabSize'];

  function caretPoint() {
    var cs = getComputedStyle(input);
    COPY.forEach(function (p) { mirror.style[p] = cs[p]; });
    mirror.style.position = 'absolute';
    mirror.style.visibility = 'hidden';
    mirror.style.whiteSpace = 'pre-wrap';
    mirror.style.overflowWrap = 'break-word';
    mirror.style.top = '0';
    mirror.style.left = '-9999px';
    var pos = input.selectionEnd || 0;
    mirror.textContent = input.value.slice(0, pos);
    var marker = document.createElement('span');
    marker.textContent = '​';
    mirror.appendChild(marker);
    document.body.appendChild(mirror);
    var r = input.getBoundingClientRect();
    var x = r.left + marker.offsetLeft - input.scrollLeft;
    var y = r.top + marker.offsetTop - input.scrollTop + marker.offsetHeight / 2;
    document.body.removeChild(mirror);
    return { x: x, y: y };
  }

  function followCaret() {
    if (!input || mode === 'waiting') return;
    setMode('typing');
    var c = caretPoint();
    var e = svg.getBoundingClientRect();
    var dx = c.x - (e.left + e.width / 2);
    var dy = c.y - (e.top + e.height / 2);
    gaze.x = clamp(dx / (e.width * 0.55), -1, 1) * (MAX_X - 12);
    gaze.y = clamp(dy / (e.height * 1.2), -1, 1) * MAX_Y;
  }

  // ---- Klatka animacji ----
  function render(dtSec) {
    var t = now();
    var target, pose = POSE[mode];

    if (mode === 'waiting') {
      var wt = ((t - modeStart) / 1000) % CYCLE;
      if (lastWaitT < WAIT_BLINK_AT && wt >= WAIT_BLINK_AT) blinkStart = t;
      lastWaitT = wt;
      target = lookAt(wt);
    } else {
      target = mode === 'typing' ? gaze : { x: 0, y: 0 };
      // Naturalne mrugniecia co kilka sekund, poza trybem czekania (tam mrugniecie jest w cyklu).
      if (t > nextBlink) { blinkStart = t; nextBlink = t + 3000 + Math.random() * 4000; }
    }

    // Plynne dojscie do celu; przy czekaniu szybciej, bo ruchy sa juz wygladzone w LOOK.
    var k = 1 - Math.exp(-dtSec * (mode === 'waiting' ? 30 : 9));
    cur.x = lerp(cur.x, target.x, k);
    cur.y = lerp(cur.y, target.y, k);
    cur.up = lerp(cur.up, pose.up, k);
    cur.low = lerp(cur.low, pose.low, k);

    var b = reduce.matches ? 1 : blinkFactor(t - blinkStart);
    var up = lerp(LID_CLOSED, UP_OPEN, cur.up * b);
    var low = lerp(LID_CLOSED, LOW_OPEN, cur.low * b);
    lids.setAttribute('d', 'M20 110 Q200 ' + up.toFixed(1) + ' 380 110 Q200 ' + low.toFixed(1) + ' 20 110 Z');
    // Przy mrugnieciu teczowka na chwile zjezdza w dol.
    iris.setAttribute('transform', 'translate(' + cur.x.toFixed(1) + ' ' + (cur.y + 8 * (1 - b)).toFixed(1) + ')');
  }

  function frame() {
    var t = now();
    var dt = Math.min((t - last) / 1000, 0.1);
    last = t;
    if (!reduce.matches) render(dt);
    requestAnimationFrame(frame);
  }

  // Ograniczenie ruchu w systemie: oko stoi w spoczynku, bez rozgladania i sledzenia.
  function applyReduce() {
    if (reduce.matches) { mode = 'idle'; cur = { x: 0, y: 0, up: POSE.idle.up, low: POSE.idle.low }; render(1); }
  }
  if (reduce.addEventListener) reduce.addEventListener('change', applyReduce);
  applyReduce();

  // ---- Zdarzenia ----
  if (input) {
    ['focus', 'input', 'click', 'keyup', 'select'].forEach(function (ev) {
      input.addEventListener(ev, followCaret);
    });
    input.addEventListener('blur', function () { if (mode === 'typing') setMode('idle'); });
    window.addEventListener('scroll', function () { if (mode === 'typing') followCaret(); }, { passive: true });
  }

  if (form) {
    form.addEventListener('htmx:beforeRequest', function () { resultMood = null; setMode('waiting'); });
  }

  // Odpowiedz gotowa: kolor oka wedlug wyniku (data-outcome w templates/result.html).
  document.addEventListener('htmx:afterSettle', function () {
    if (mode !== 'waiting' || !answer || answer.querySelector('[hx-trigger]')) return;
    var result = answer.querySelector('[data-outcome]');
    resultMood = result ? result.getAttribute('data-outcome') : 'neutral';
    setMode('idle');
  });
  function failed() {
    if (mode !== 'waiting') return;
    resultMood = 'neutral';
    setMode('idle');
  }
  document.addEventListener('htmx:afterRequest', function (e) { if (!e.detail.successful) failed(); });
  document.addEventListener('htmx:sendError', failed);

  requestAnimationFrame(frame);
})();
