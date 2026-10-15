/* Shared behaviour for NanaFitMama sub-pages: progress bar, sticky nav, mobile menu, scroll reveal. */
// Progress bar
var bar = document.getElementById('bar');
window.addEventListener('scroll', function() {
  bar.style.width = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight) * 100) + '%';
}, {passive:true});

// Nav scroll
var nav = document.getElementById('nav');
window.addEventListener('scroll', function() {
  nav.classList.toggle('scrolled', window.scrollY > 60);
}, {passive:true});

// Mobile nav
document.getElementById('navToggle').addEventListener('click', function() {
  nav.classList.toggle('nav-open');
});
document.querySelectorAll('.nav-links a').forEach(function(a) {
  a.addEventListener('click', function() { nav.classList.remove('nav-open'); });
});

// Smooth anchor scroll
document.querySelectorAll('a[href^="#"]').forEach(function(a) {
  a.addEventListener('click', function(e) {
    var id = a.getAttribute('href');
    if (id === '#') return;
    var t = document.querySelector(id);
    if (t) { e.preventDefault(); window.scrollTo({top: t.getBoundingClientRect().top + window.scrollY - 80, behavior:'smooth'}); }
  });
});

// Scroll reveal
var obs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) { if (e.isIntersecting) { e.target.classList.add('up'); obs.unobserve(e.target); } });
}, {threshold:.1, rootMargin:'0px 0px -50px 0px'});
document.querySelectorAll('.rv,.rl,.rr').forEach(function(el) { obs.observe(el); });

// Image fallbacks (the tinted placeholder behind each photo stays visible)
document.querySelectorAll('img').forEach(function(img) {
  img.onerror = function() { this.style.display = 'none'; };
});
