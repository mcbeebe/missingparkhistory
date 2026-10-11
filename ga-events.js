/* GA4 custom events for support, signup and help actions, shared by every page.
   Listens on the document, so links and forms need no extra markup; the
   existing data-umami-event label (if any) is reused as the "location".
     kofi_click             any link to ko-fi.com
     sign_up                Weekly Watch (Buttondown) form submitted with a valid email
     volunteer_signup_click link to the volunteer-monitor Google Form
     subscribe_click        a Subscribe button or ?subscribe=1 link (opens the signup box)
     help_click             any link to the Help page (location: nav, footer, or the button)
     help_action            a call-to-action button on the Help page itself
     shop_click             any link to shop.missingparkhistory.org
     timeline_filter        a type button on the timeline (filter, results)
     news_filter            a News & Press topic button, Month/Source menu, or Clear (filter_type, value, results)
   Take Action panel steps (take_action_open, _zip_lookup, _contact_click, ...)
   are sent by taTrack() in index.html, not here. */
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

  function onPage(name) {
    return new RegExp('/' + name + '(\\.html)?$').test(location.pathname);
  }

  // Count what is still showing once the page's own filter handler has run.
  function afterFilter(selector, fn) {
    setTimeout(function () { fn(document.querySelectorAll(selector).length); }, 0);
  }

  function isHelpPage() {
    return /\/help(\.html)?$/.test(location.pathname);
  }

  // Where a link sits: its Umami label, else the nav/footer it is in, else its own text.
  function placement(el) {
    if (label(el)) return label(el);
    if (el.closest('nav, .topnav, .topnav-links')) return 'nav';
    if (el.closest('footer, .page-footer, .footer')) return 'footer';
    if (el.closest('#taOverlay')) return 'take-action-panel';
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

    var fb = e.target.closest('.filter-btn[data-filter], #clearFilters');
    if (fb && onPage('timeline')) {
      afterFilter('.timeline-event:not(.hidden)', function (n) {
        send('timeline_filter', { filter: fb.dataset.filter, results: n });
      });
    } else if (fb && onPage('news-and-press')) {
      var clear = fb.id === 'clearFilters';
      afterFilter('.article-card:not(.hidden)', function (n) {
        send('news_filter', { filter_type: clear ? 'clear' : 'topic', value: clear ? 'all' : fb.dataset.filter, results: n });
      });
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
    } else if (/^https?:\/\/shop\.missingparkhistory\.org/i.test(href)) {
      send('shop_click', { location: placement(a), link_url: href });
    } else if (a.origin === location.origin && /\/help(\.html)?$/.test(a.pathname) && !isHelpPage()) {
      send('help_click', { location: placement(a), link_text: text(a) });
    }
  }, true);

  document.addEventListener('change', function (e) {
    var sel = e.target;
    if (!onPage('news-and-press') || !sel || !/^filter(Month|Source)$/.test(sel.id)) return;
    afterFilter('.article-card:not(.hidden)', function (n) {
      send('news_filter', { filter_type: sel.id === 'filterMonth' ? 'month' : 'source', value: sel.value, results: n });
    });
  }, true);

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !/buttondown\.com/i.test(form.action || '')) return;
    if (form.checkValidity && !form.checkValidity()) return;
    var btn = form.querySelector('[type="submit"]');
    send('sign_up', { method: 'weekly_watch', location: (btn && label(btn)) || form.id || 'unlabeled' });
  }, true);
})();
