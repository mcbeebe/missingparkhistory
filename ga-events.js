/* GA4 custom events for support and signup actions, shared by every page.
   Listens on the document, so links and forms need no extra markup; the
   existing data-umami-event label (if any) is reused as the "location".
     kofi_click             any link to ko-fi.com
     sign_up                Weekly Watch (Buttondown) form submitted with a valid email
     volunteer_signup_click link to the volunteer-monitor Google Form */
(function () {
  if (window.mphGaEvents) return;
  window.mphGaEvents = true;

  function send(name, params) {
    if (typeof window.gtag !== 'function') return;
    params.page_path = location.pathname;
    window.gtag('event', name, params);
  }

  function label(el) {
    var tagged = el.closest('[data-umami-event]');
    return tagged ? tagged.getAttribute('data-umami-event') : '';
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.href;
    if (/^https?:\/\/(www\.)?ko-fi\.com\//i.test(href)) {
      send('kofi_click', { location: label(a) || 'unlabeled', link_url: href });
    } else if (/docs\.google\.com\/forms\//i.test(href)) {
      send('volunteer_signup_click', { location: label(a) || 'unlabeled', link_url: href });
    }
  }, true);

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !/buttondown\.com/i.test(form.action || '')) return;
    if (form.checkValidity && !form.checkValidity()) return;
    var btn = form.querySelector('[type="submit"]');
    send('sign_up', { method: 'weekly_watch', location: (btn && label(btn)) || form.id || 'unlabeled' });
  }, true);
})();
