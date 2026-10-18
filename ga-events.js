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
   Voices:
     voices_link_click      a link to /voices.html from another page (location)
     voices_river_pause     Pause/Resume on the quote river (state: paused|resumed)
     voices_quote_click     a park link inside a river quote (park, park_slug, destination park_page|map)
     voices_cta_click       Methodology / Back to the map / About buttons (link_text)
     (voices_park_open and voices_layer_toggle are sent from voices.html / index.html)
   Blocked funding layer (sent from index.html):
     funding_layer_toggle   the "Blocked funding" pill (state: on|off)
     funding_lens           History & collections / All chip (lens: hist|all)
     funding_park_open      a funding ring is clicked (park_code, park, agreements, usd, lens)
     funding_offmap_open    the "not on the map" button (usd)
   Status page:
     status_link_click      a link in the page body (section, link_type source|internal|external|email,
                            link_text, link_domain); section is verdict, stats, lane:<x>, case:<x>,
                            this_week, info_box, cta or other
     status_section_view    once per section as it scrolls into view (section, position)
   President's House (presidents-house.html = main, presidents-house-update.html = update):
     ph_photo_open          a panel photo is opened (page, panel, version before|after|restored|stripped|
                            original|proposed)
     ph_link_click          a link in the page body (page, link_type footnote|internal|external, link_text,
                            link_domain, footnote)
     ph_popup_close         update page intro popup dismissed (method close_button|backdrop|escape|
                            read_full|take_action)
     ph_take_action_click   update page Take Action button (location popup|page)
   Sent from index.html itself: map_park_open, map_photo_open, share (copy_link),
   and the Take Action steps via taTrack(). park_photo_open (park, gallery,
   photo_index, photos) is sent by photo-viewer.js when it opens a park-page gallery;
   it also sends photo_zoom and photo_nav for both the map and park pages. */
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
    if (onPage('voices')) voicesClick(e.target);
    if (onPage('status')) statusClick(e.target);
    if (phPage()) phClick(e.target);
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
    } else if (a.origin === location.origin && /\/voices(\.html)?$/.test(a.pathname) && !onPage('voices')) {
      send('voices_link_click', { location: placement(a) });
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

  function voicesClick(t) {
    var pause = t.closest('#riverPause');
    if (pause) {
      return afterFilter('body', function () {
        send('voices_river_pause', { state: pause.getAttribute('aria-pressed') === 'true' ? 'paused' : 'resumed' });
      });
    }
    var quote = t.closest('#riverTrack cite a');
    if (quote) {
      var m = quote.pathname.match(/\/parks\/([^\/]+?)(\.html)?$/);
      return send('voices_quote_click', {
        park: text(quote), park_slug: m ? m[1] : '', destination: quote.getAttribute('data-dest') || 'park_page'
      });
    }
    var cta = t.closest('.cta-links a');
    if (cta) send('voices_cta_click', { link_text: text(cta) });
  }

  function statusSection(el) {
    var lane = el.closest('.lane[data-lane]');
    if (lane) return 'lane:' + lane.getAttribute('data-lane');
    var kase = el.closest('.case[data-case]');
    if (kase) return 'case:' + kase.getAttribute('data-case');
    if (el.closest('.nd-synthesis')) return 'this_week';
    if (el.closest('.stats-grid')) return 'stats';
    if (el.closest('.hero, .verdict')) return 'verdict';
    if (el.closest('.info-box')) return 'info_box';
    if (el.closest('.cta-section')) return 'cta';
    return 'other';
  }

  function statusClick(t) {
    var a = t.closest('.page-wrapper a[href]');
    if (!a || a.closest('nav, .topnav, footer, .page-footer')) return;
    var type = /^mailto:/i.test(a.href) ? 'email'
      : a.classList.contains('src') ? 'source'
      : a.origin === location.origin ? 'internal' : 'external';
    send('status_link_click', {
      section: statusSection(a), link_type: type, link_text: text(a),
      link_domain: type === 'email' ? '' : a.hostname
    });
  }

  // Status page: one status_section_view per section, when its top passes 60% of the viewport.
  function watchStatusSections() {
    if (!onPage('status') || !('IntersectionObserver' in window)) return;
    var SECTIONS = [['.verdict', 'verdict'], ['.stats-grid', 'stats'], ['.lanes', 'four_fronts'],
      ['.case-board', 'cases'], ['.nd-synthesis', 'this_week'], ['.cta-section', 'cta']];
    var names = new Map();
    SECTIONS.forEach(function (s, i) {
      var el = document.querySelector(s[0]);
      if (el) names.set(el, { section: s[1], position: i + 1 });
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var info = names.get(en.target);
        if (!en.isIntersecting || !info) return;
        names.delete(en.target);   // once per section
        io.unobserve(en.target);
        send('status_section_view', Object.assign({}, info));
      });
    }, { rootMargin: '0px 0px -40% 0px' });
    names.forEach(function (_, el) { io.observe(el); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchStatusSections);
  else watchStatusSections();

  function phPage() {
    return onPage('presidents-house') ? 'main' : onPage('presidents-house-update') ? 'update' : '';
  }

  // "Oney Escapes - before removal" / "Original panel: Oney Escapes!, telling ..."
  function phPhoto(alt) {
    var m = alt.match(/^(Original|Proposed)[^:]*:\s*([^,]+)/i);
    if (m) return { panel: m[2].trim(), version: m[1].toLowerCase() };
    m = alt.match(/^(.*?)\s+-\s+(\w+)/);
    return m ? { panel: m[1].trim(), version: m[2].toLowerCase() } : { panel: alt.slice(0, 80), version: '' };
  }

  function phPopupOpen() {
    var o = document.getElementById('popupOverlay');
    return !!(o && o.classList.contains('active'));
  }

  function phClick(t) {
    var page = phPage();
    var img = t.closest('.image-container img, .photo-card img');
    if (img) {
      var info = phPhoto(img.getAttribute('alt') || '');
      return send('ph_photo_open', { page: page, panel: info.panel, version: info.version });
    }
    if (page === 'update' && phPopupOpen()) {
      var method = t.closest('#popupClose') ? 'close_button'
        : t.id === 'popupOverlay' ? 'backdrop'
        : t.closest('.popup-btn-primary') ? 'read_full'
        : t.closest('[onclick*="openTakeAction"]') ? 'take_action' : '';
      if (method) send('ph_popup_close', { method: method });
    }
    var ta = t.closest('[onclick*="openTakeAction"]');
    if (ta) return send('ph_take_action_click', { page: page, location: ta.closest('#popupOverlay') ? 'popup' : 'page' });
    var a = t.closest('a[href]');
    if (!a || a.closest('nav, .topnav, footer, .page-footer') || a.getAttribute('href') === '#') return;
    if (/ko-fi\.com/i.test(a.href)) return;   // kofi_click covers these
    var cite = a.classList.contains('cite-link') || /^#fn\d+/.test(a.getAttribute('href'));
    send('ph_link_click', {
      page: page,
      link_type: cite ? 'footnote' : a.origin === location.origin ? 'internal' : 'external',
      link_text: text(a), link_domain: cite ? '' : a.hostname,
      footnote: cite ? a.getAttribute('href').slice(1) : ''
    });
  }

  // Esc on the update page: count it only if it actually closed the intro popup (an Esc
  // that closes the photo viewer stops there and leaves the popup open).
  window.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || phPage() !== 'update' || !phPopupOpen()) return;
    setTimeout(function () {
      if (!phPopupOpen()) send('ph_popup_close', { method: 'escape' });
    }, 0);
  }, true);

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
