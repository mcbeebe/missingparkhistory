/**
 * Shared site header behaviour for every page with `nav.topnav`.
 *
 * Adds a menu button and collapses `.topnav-links` into a dropdown whenever the
 * links don't fit on one row beside the brand (phones, tablets, narrow windows).
 * Include synchronously right after `</nav>` so the collapsed state is set
 * before first paint:  <script src="/site-nav.js"></script>
 * Styles live in /site-nav.css.
 */
(function () {
  var nav = document.querySelector('nav.topnav');
  if (!nav || nav.classList.contains('nav-js')) return;
  var links = nav.querySelector('.topnav-links');
  var brand = nav.querySelector('.topnav-brand');
  if (!links) return;

  if (!links.id) links.id = 'site-nav-links';
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'nav-toggle';
  btn.setAttribute('aria-controls', links.id);
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-label', 'Open menu');
  btn.innerHTML = '<span class="nav-toggle-bars" aria-hidden="true"></span>';
  if (brand) btn.style.color = getComputedStyle(brand).color;
  // The bar is translucent with a backdrop blur; the dropdown needs a solid fill.
  function solid(el) {
    var c = el && getComputedStyle(el).backgroundColor.match(/[\d.]+/g);
    return c && c.length >= 3 && c[3] !== '0' ? 'rgb(' + c.slice(0, 3).join(',') + ')' : null;
  }
  links.style.setProperty('--nav-menu-bg', solid(nav) || solid(document.body) || '#fff');
  nav.insertBefore(btn, links);
  nav.classList.add('nav-js');

  function setOpen(open) {
    nav.classList.toggle('nav-open', open);
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }

  /** Collapse when brand + full link row would not fit inside the bar. */
  function update() {
    nav.classList.remove('nav-collapsed');
    var items = links.children;
    var collapse = false;
    if (items.length) {
      var cs = getComputedStyle(nav);
      var avail = nav.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      var row = items[items.length - 1].getBoundingClientRect().right - items[0].getBoundingClientRect().left;
      var brandW = brand ? brand.getBoundingClientRect().width : 0;
      collapse = brandW + (parseFloat(cs.columnGap) || 0) + row > avail;
    }
    nav.classList.toggle('nav-collapsed', collapse);
    if (!collapse) setOpen(false);
  }

  btn.addEventListener('click', function () {
    setOpen(!nav.classList.contains('nav-open'));
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && nav.classList.contains('nav-open')) {
      setOpen(false);
      btn.focus();
    }
  });
  document.addEventListener('click', function (e) {
    if (nav.classList.contains('nav-open') && !nav.contains(e.target)) setOpen(false);
  });
  links.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('a')) setOpen(false);
  });

  var pending = false;
  window.addEventListener('resize', function () {
    if (pending) return;
    pending = true;
    requestAnimationFrame(function () { pending = false; update(); });
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(update);
  window.addEventListener('load', update);
  update();
})();
