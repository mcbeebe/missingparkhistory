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
   Map (homepage):
     map_filter             Status/Topic/Media option, State menu, filter chip removed, Clear All
                            (filter_type, value, selected, results = markers still on the map)
     search                 a map search result is picked (search_term, park, entry_id)
     map_park_page_click    a link from the map to a parks/ page (park_slug)
   Park pages (parks/*.html) and any page with the share bar:
     share                  share bar button (method, content_type, item_id)
     park_map_click         View on map / Open Interactive Map (location)
     park_source_click      a news source or park-history source link (section, link_domain)
   Sent from index.html itself: map_park_open, map_photo_open, share (copy_link),
   and the Take Action steps via taTrack(). park_photo_open (park, gallery,
   photo_index, photos) is sent by park-photos.js when its viewer opens. */
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

  function isHome() {
    return /^\/(index\.html)?$/.test(location.pathname);
  }

  function parkSlug() {
    var m = location.pathname.match(/\/parks\/([^\/]+?)(\.html)?$/);
    return m ? m[1] : '';
  }

  function mapResults() {
    return typeof clusterGroup !== 'undefined' && clusterGroup.getLayers ? clusterGroup.getLayers().length : -1;
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

    if (isHome()) mapClick(e.target);
    if (parkSlug() || e.target.closest('.share-bar')) parkClick(e.target);

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

  function mapClick(t) {
    var opt = t.closest('.ms-dd-opt[data-val]');
    if (opt) {
      var panel = opt.closest('[id$="Panel"]');
      var type = panel ? panel.id.replace(/Panel$/, '') : 'unknown';
      return afterFilter('body', function () {
        send('map_filter', { filter_type: type, value: opt.getAttribute('data-val'), selected: opt.classList.contains('sel'), results: mapResults() });
      });
    }
    var chip = t.closest('#filterChips [onclick]');
    if (chip) {
      var m = (chip.getAttribute('onclick') || '').match(/rem(\w+)\('([^']*)'/);
      return afterFilter('body', function () {
        send('map_filter', { filter_type: m ? m[1].toLowerCase() : 'chip', value: m ? m[2] : '', selected: false, results: mapResults() });
      });
    }
    if (t.closest('#clearAllBtn')) {
      return afterFilter('body', function () {
        send('map_filter', { filter_type: 'clear', value: 'all', selected: false, results: mapResults() });
      });
    }
    var hit = t.closest('.search-result');
    if (hit) {
      var input = document.getElementById('searchInput');
      var id = (hit.getAttribute('onclick') || '').match(/goToEntry\('([^']*)'/);
      var park = hit.querySelector('.sr-park');
      return send('search', { search_term: input ? input.value.trim().slice(0, 100) : '', park: park ? text(park) : '', entry_id: id ? id[1] : '' });
    }
    var pl = t.closest('a[href*="parks/"]');
    if (pl) {
      var slugM = pl.pathname.match(/\/parks\/([^\/]+?)(\.html)?$/);
      if (slugM) send('map_park_page_click', { park_slug: slugM[1] });
    }
  }

  var SHARE_METHODS = { tw: 'twitter', bs: 'bluesky', fb: 'facebook', rd: 'reddit', cl: 'copy_link' };

  function parkClick(t) {
    var park = parkSlug();
    var sh = t.closest('.share-btn');
    if (sh) {
      var method = 'other';
      for (var k in SHARE_METHODS) if (sh.classList.contains(k)) method = SHARE_METHODS[k];
      return send('share', { method: method, content_type: park ? 'park_page' : 'page', item_id: park || location.pathname });
    }
    if (!park) return;
    var mapLink = t.closest('.view-map-link, .cta-btn');
    if (mapLink) return send('park_map_click', { park: park, location: mapLink.classList.contains('cta-btn') ? 'cta' : 'view-on-map' });
    var src = t.closest('.news-source-item, .park-history-section a[href^="http"]');
    if (src) {
      send('park_source_click', { park: park, section: src.classList.contains('news-source-item') ? 'news' : 'history', link_domain: src.hostname, link_url: src.href });
    }
  }

  document.addEventListener('change', function (e) {
    var sel = e.target;
    if (isHome() && sel && sel.id === 'stateSel') {
      return afterFilter('body', function () {
        send('map_filter', { filter_type: 'state', value: sel.value || 'all', selected: !!sel.value, results: mapResults() });
      });
    }
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
