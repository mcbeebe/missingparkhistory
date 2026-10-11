/* GA4 custom events for support, signup and help actions, shared by every page.
   Listens on the document, so links and forms need no extra markup; the
   existing data-umami-event label (if any) is reused as the "location".
     kofi_click             any link to ko-fi.com
     sign_up                Weekly Watch (Buttondown) form submitted with a valid email
     volunteer_signup_click link to the volunteer-monitor Google Form
     subscribe_click        a Subscribe button or ?subscribe=1 link (opens the signup box)
     help_click             any link to the Help page (location: nav, footer, or the button)
     help_action            a call-to-action button on the Help page itself */
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

  function slug(s) {
    return (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);
  }

  function text(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100);
  }

  function isHelpPage() {
    return /\/help(\.html)?$/.test(location.pathname);
  }

  // Where a link sits: its Umami label, else the nav/footer it is in, else its own text.
  function placement(el) {
    if (label(el)) return label(el);
    if (el.closest('nav, .topnav, .topnav-links')) return 'nav';
    if (el.closest('footer, .page-footer, .footer')) return 'footer';
    return slug(text(el)) || 'unlabeled';
  }

  // The Help page's buttons: tier cards (.act), the four "fronts", and the support box.
  var HELP_ACTIONS = '.act a.go, .act button, .front a.primary, .front button, .support .btns a';

  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;

    if (isHelpPage()) {
      var act = e.target.closest(HELP_ACTIONS);
      if (act) {
        var card = act.closest('.act, .front, .support');
        var heading = card && card.querySelector('h3, h2');
        send('help_action', {
          action: label(act) || slug(heading ? text(heading) : text(act)) || 'unlabeled',
          section: heading ? text(heading) : '',
          link_text: text(act),
          link_url: act.href || ''
        });
      }
    }

    var sub = e.target.closest('.sub-btn, a[href*="subscribe=1"]');
    if (sub) send('subscribe_click', { location: label(sub) || placement(sub) });

    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.href;
    if (/^https?:\/\/(www\.)?ko-fi\.com\//i.test(href)) {
      send('kofi_click', { location: label(a) || 'unlabeled', link_url: href });
    } else if (/docs\.google\.com\/forms\//i.test(href)) {
      send('volunteer_signup_click', { location: label(a) || 'unlabeled', link_url: href });
    } else if (a.origin === location.origin && /\/help(\.html)?$/.test(a.pathname) && !isHelpPage()) {
      send('help_click', { location: placement(a), link_text: text(a) });
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
