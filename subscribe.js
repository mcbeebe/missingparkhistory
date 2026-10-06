/* Weekly Watch signup card, shared by all content pages.
   Inserted just above the page footer; posts to Buttondown (double opt-in).
   Edit this one file to change the signup everywhere. */
(function () {
  if (document.getElementById('wwSub') || document.getElementById('ndSubForm')) return;
  if (document.body.classList.contains('embed-mode')) return;

  var ACTION = 'https://buttondown.com/api/emails/embed-subscribe/missingparkhistory';

  var css =
    '.ww-sub{max-width:640px;margin:40px auto 8px;padding:24px 26px;border-radius:14px;' +
    'background-color:#1B4332;color:#e8efe9;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
    'box-shadow:0 8px 30px rgba(0,0,0,.18);box-sizing:border-box}' +
    '.ww-sub *{box-sizing:border-box}' +
    '.ww-sub h2{margin:0 0 6px;font-family:Georgia,"Times New Roman",serif;font-size:21px;line-height:1.3;color:#fff;font-weight:700}' +
    '.ww-sub p{margin:0 0 14px;font-size:14px;line-height:1.55;color:#c9dccf}' +
    '.ww-sub form{display:flex;gap:8px;margin:0}' +
    '.ww-sub input{flex:1;min-width:0;padding:11px 13px;border-radius:9px;border:1px solid #3d6b55;' +
    'background:#10291f;color:#fff;font-size:15px;font-family:inherit}' +
    '.ww-sub input::placeholder{color:#8fb09e}' +
    '.ww-sub input:focus{outline:2px solid #fbbf24;outline-offset:1px}' +
    '.ww-sub button{padding:11px 18px;border-radius:9px;border:0;background:#fbbf24;color:#1B4332;' +
    'font-weight:800;font-size:15px;cursor:pointer;white-space:nowrap;font-family:inherit}' +
    '.ww-sub button:hover{background:#fcd34d}' +
    '.ww-sub .ww-fine{margin:10px 0 0;font-size:12px;color:#8fb09e}' +
    '.ww-sub .ww-ok{margin:0;font-size:15px;font-weight:700;color:#86efac}' +
    '@media(max-width:520px){.ww-sub{margin:28px 12px 8px;padding:20px}.ww-sub form{flex-direction:column}.ww-sub button{width:100%}}';

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var box = document.createElement('section');
  box.className = 'ww-sub';
  box.id = 'wwSub';
  box.setAttribute('aria-labelledby', 'wwSubTitle');
  box.innerHTML =
    '<h2 id="wwSubTitle">&#128236; Get the Weekly Watch</h2>' +
    '<p>One email every Monday: what changed in America&rsquo;s parks this week, and one thing you can do about it.</p>' +
    '<form id="wwSubForm" action="' + ACTION + '" method="post" target="_blank">' +
      '<input type="email" name="email" id="wwSubEmail" placeholder="you@email.com" aria-label="Email address" required>' +
      '<button type="submit" data-umami-event="subscribe-page">Subscribe</button>' +
    '</form>' +
    '<p class="ww-ok" id="wwSubOk" hidden>&#10003; Thanks! Check your inbox to confirm your subscription.</p>' +
    '<p class="ww-fine">Free. Unsubscribe anytime.</p>';

  var anchor = document.querySelector('.page-footer') || document.querySelector('.footer');
  if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor);
  else document.body.appendChild(box);

  var form = document.getElementById('wwSubForm');
  form.addEventListener('submit', function (e) {
    var inp = document.getElementById('wwSubEmail');
    if (!inp.checkValidity()) return; // let the browser show the error
    e.preventDefault();
    try {
      fetch(ACTION, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'email=' + encodeURIComponent(inp.value)
      });
    } catch (err) { form.submit(); return; }
    form.hidden = true;
    document.getElementById('wwSubOk').hidden = false;
  });
})();
